def train(
    base_model:        str   = "unsloth/orpheus-3b-0.1-pretrained",
    hf_dataset:        str   = "afkfatih/turkish-tts-combined-raw",
    checkpoint_dir:    str   = "/data/orpheus/checkpoints/turkish",
    data_dir:          str   = "",        # preprocessed data; defaults to checkpoint_dir/../preprocessed
    hf_cache:          str   = "/data/orpheus/hf-cache",
    max_samples:       int   = 0,        # 0 = full dataset
    max_seq_len:       int   = 4096,
    batch_size:        int   = 2,
    grad_accum:        int   = 4,
    learning_rate:     float = 1e-4,
    num_epochs:        int   = 3,
    save_steps:        int   = 200,
    logging_steps:     int   = 10,
    eval_steps:        int   = 0,        # 0 = use audio_log_steps
    audio_log_steps:   int   = 100,
    eval_split:        float = 0.05,
    warmup_ratio:      float = 0.05,
    lora_r:            int   = 16,
    lora_alpha:        int   = 32,
    lora_dropout:      float = 0.05,
    mlflow_experiment: str   = "orpheus-turkish-tts",
    # Whisper model for in-training WER/CER — keep small/medium for speed.
    # large-v3 is used in the post-training eval job only.
    whisper_model:     str   = "small",
):
    """
    Self-contained Orpheus-3B Turkish TTS fine-tuning.
    All imports, constants, helpers, and callbacks are defined inside this
    function so cloudpickle can serialize it without any external dependencies.
    """

    # ── Stdlib / lightweight imports (always available) ──────────────────────
    import logging
    import math
    import os
    import sys
    import tempfile
    import time
    from pathlib import Path
    from typing import Optional

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    log = logging.getLogger("train_orpheus")

    # ── Heavy ML imports ──────────────────────────────────────────────────────
    import warnings

    import urllib3

    warnings.filterwarnings("ignore", category=urllib3.exceptions.InsecureRequestWarning)

    import librosa
    import matplotlib.pyplot as plt
    import mlflow
    import numpy as np
    import soundfile as sf
    import torch
    from datasets import load_from_disk
    from peft import LoraConfig, TaskType, get_peft_model
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        DataCollatorForSeq2Seq,
        Trainer,
        TrainerCallback,
        TrainingArguments,
    )

    # ── Constants (Orpheus / SNAC token spec) ─────────────────────────────────
    LLAMA_VOCAB    = 128_256
    CODE_OFFSET    = LLAMA_VOCAB + 10   # 128266 — first audio token ID
    N_CODEBOOK     = 4_096              # codebook entries per SNAC layer
    N_PER_FRAME    = 7                  # 1+2+4 tokens per SNAC-24kHz frame
    SNAC_SR        = 24_000

    TOK_SOH = LLAMA_VOCAB + 3   # start_of_human
    TOK_EOH = LLAMA_VOCAB + 4   # end_of_human
    TOK_SOA = LLAMA_VOCAB + 5   # start_of_ai
    TOK_EOA = LLAMA_VOCAB + 6   # end_of_ai
    TOK_SOS = LLAMA_VOCAB + 1   # start_of_speech
    TOK_EOT = LLAMA_VOCAB + 9   # end_of_text

    EVAL_SENTENCES = [
        ("flight_announce", "sayın yolcularımız, uçuşumuz yaklaşık iki saat sürecektir."),
        ("welcome",         "istanbul'a hoş geldiniz."),
        ("safety",          "güvenlik nedeniyle elektronik cihazlarınızı kapalı tutunuz."),
        ("farewell",        "teşekkür ederiz, iyi yolculuklar dileriz."),
    ]

    GEN_MAX_NEW_TOKENS = int(os.environ.get("GEN_MAX_NEW_TOKENS", "1500"))
    GEN_MIN_NEW_TOKENS = int(os.environ.get("GEN_MIN_NEW_TOKENS", "80"))
    GEN_BASELINE_MAX_NEW_CAP = int(os.environ.get("GEN_BASELINE_MAX_NEW_CAP", "400"))
    GEN_TEMPERATURE    = float(os.environ.get("GEN_TEMPERATURE", "0.3"))
    GEN_TOP_P          = float(os.environ.get("GEN_TOP_P", "0.9"))
    GEN_REPETITION_PENALTY = float(os.environ.get("GEN_REPETITION_PENALTY", "1.15"))
    GEN_TRIM_TOP_DB    = float(os.environ.get("GEN_TRIM_TOP_DB", "28"))

    # ── Environment setup ─────────────────────────────────────────────────────
    os.environ["HF_HOME"]               = hf_cache
    os.environ.setdefault("MLFLOW_EXPERIMENT_NAME", mlflow_experiment)
    is_main = int(os.environ.get("RANK", "0")) == 0

    out_dir = Path(checkpoint_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Filled after dataset load; consumed inside on_train_begin (run is active by then)
    _dataset_params: dict = {}
    effective_eval_steps = eval_steps or audio_log_steps

    # ── Helper: build inference prompt ────────────────────────────────────────
    def build_prompt(tokenizer, text: str) -> list:
        # Match preprocess(): no BOS/EOS from tokenizer — header tokens added explicitly.
        ids = tokenizer.encode(text, add_special_tokens=False) + [TOK_EOT]
        return [TOK_SOH] + ids + [TOK_EOH, TOK_SOA, TOK_SOS]

    def _min_new_tokens_for(text: str) -> int:
        mult = int(os.environ.get("GEN_MIN_TOKENS_PER_CHAR", "7"))
        return min(
            GEN_MAX_NEW_TOKENS - 50,
            max(GEN_MIN_NEW_TOKENS, len(text) * mult),
        )

    def _generation_budget(text: str, *, baseline: bool) -> tuple[int, int]:
        if baseline:
            return GEN_MIN_NEW_TOKENS, min(GEN_MAX_NEW_TOKENS, GEN_BASELINE_MAX_NEW_CAP)
        return _min_new_tokens_for(text), GEN_MAX_NEW_TOKENS

    def _truncate_at_eoa(token_ids: list) -> list:
        if TOK_EOA in token_ids:
            return token_ids[: token_ids.index(TOK_EOA)]
        return token_ids

    def _clean_wav(wav: np.ndarray) -> np.ndarray:
        """Trim edge silence only — keep full utterance including brief pauses."""
        wav = wav.astype(np.float32)
        try:
            trimmed, _ = librosa.effects.trim(
                wav, top_db=GEN_TRIM_TOP_DB, frame_length=2048, hop_length=512,
            )
            if len(trimmed) / SNAC_SR >= 0.1:
                wav = trimmed
        except Exception:
            pass

        peak = np.abs(wav).max()
        if peak > 1e-6:
            wav = wav * (0.9 / peak)
        return wav.astype(np.float32)

    # ── Helper: decode SNAC audio tokens → waveform ───────────────────────────
    def snac_decode(snac_model, token_ids: list, device) -> Optional[np.ndarray]:
        """
        Interleaving per frame (7 tokens):
          pos 0 → layer0[f]
          pos 1 → layer1[2f],  pos 4 → layer1[2f+1]
          pos 2 → layer2[4f],  pos 3 → layer2[4f+1]
          pos 5 → layer2[4f+2], pos 6 → layer2[4f+3]
        """
        audio_ids = [t for t in token_ids if t >= CODE_OFFSET]
        n = len(audio_ids) // N_PER_FRAME
        if n == 0:
            return None
        audio_ids = audio_ids[:n * N_PER_FRAME]

        l0, l1, l2 = [], [], []
        for f in range(n):
            g = audio_ids[N_PER_FRAME * f : N_PER_FRAME * (f + 1)]
            l0.append((g[0] - CODE_OFFSET) % N_CODEBOOK)
            l1.append((g[1] - CODE_OFFSET) % N_CODEBOOK)
            l2.append((g[2] - CODE_OFFSET) % N_CODEBOOK)
            l2.append((g[3] - CODE_OFFSET) % N_CODEBOOK)
            l1.append((g[4] - CODE_OFFSET) % N_CODEBOOK)
            l2.append((g[5] - CODE_OFFSET) % N_CODEBOOK)
            l2.append((g[6] - CODE_OFFSET) % N_CODEBOOK)

        def _t(x): return torch.tensor(x, dtype=torch.long).unsqueeze(0).to(device)
        wav = snac_model.decode([_t(l0), _t(l1), _t(l2)])
        return wav.squeeze().cpu().float().detach().numpy()

    # ── Helper: generate audio for one sentence ───────────────────────────────
    # Detect MLflow tracing support (requires MLflow >= 2.14)
    _has_trace = hasattr(mlflow, "start_span")

    def generate_audio(
        model, tokenizer, snac_model, text: str, device,
        step: int = 0, *, baseline: bool = False,
    ):
        """Returns (waveform_or_None, elapsed_seconds). Traced with sub-spans when MLflow supports it."""

        def _run(text):
            t0 = time.perf_counter()

            # ── span 1: tokenise ──────────────────────────────────────────────
            if _has_trace:
                with mlflow.start_span(name="tokenise", span_type="PARSER") as sp:
                    prompt = build_prompt(tokenizer, text)
                    sp.set_inputs({"text": text, "baseline": baseline})
                    sp.set_outputs({"n_tokens": len(prompt)})
            else:
                prompt = build_prompt(tokenizer, text)

            inp = torch.tensor([prompt], dtype=torch.long, device=device)
            min_new, max_new = _generation_budget(text, baseline=baseline)

            # ── span 2: model.generate ────────────────────────────────────────
            if _has_trace:
                with mlflow.start_span(name="model_generate", span_type="LLM") as sp:
                    sp.set_inputs({
                        "prompt_tokens": len(prompt),
                        "max_new_tokens": max_new,
                        "min_new_tokens": min_new,
                        "baseline": baseline,
                        "temperature": GEN_TEMPERATURE,
                        "top_p": GEN_TOP_P,
                        "repetition_penalty": GEN_REPETITION_PENALTY,
                    })
                    with torch.inference_mode():
                        out = model.generate(
                            inp,
                            max_new_tokens=max_new,
                            min_new_tokens=min_new,
                            do_sample=True,
                            temperature=GEN_TEMPERATURE,
                            top_p=GEN_TOP_P,
                            use_cache=True,
                            repetition_penalty=GEN_REPETITION_PENALTY,
                            eos_token_id=TOK_EOA,
                        )
                    new_tokens = len(out[0]) - len(prompt)
                    sp.set_outputs({"generated_tokens": new_tokens})
            else:
                with torch.inference_mode():
                    out = model.generate(
                        inp,
                        max_new_tokens=max_new,
                        min_new_tokens=min_new,
                        do_sample=True,
                        temperature=GEN_TEMPERATURE,
                        top_p=GEN_TOP_P,
                        use_cache=True,
                        repetition_penalty=GEN_REPETITION_PENALTY,
                        eos_token_id=TOK_EOA,
                    )

            new_ids = _truncate_at_eoa(out[0][len(prompt) :].cpu().tolist())

            # ── span 3: SNAC decode ───────────────────────────────────────────
            if _has_trace:
                with mlflow.start_span(name="snac_decode", span_type="RETRIEVER") as sp:
                    sp.set_inputs({"audio_tokens": len(new_ids)})
                    wav = snac_decode(snac_model, new_ids, device)
                    duration = len(wav) / SNAC_SR if wav is not None else 0.0
                    sp.set_outputs({"duration_s": round(duration, 3),
                                    "sample_rate": SNAC_SR,
                                    "samples": len(wav) if wav is not None else 0})
            else:
                wav = snac_decode(snac_model, new_ids, device)

            elapsed = time.perf_counter() - t0

            if wav is not None:
                duration = len(wav) / SNAC_SR
                rtf = elapsed / max(duration, 1e-6)
                try:
                    mlflow.log_metric("rtf_latest", rtf, step=step)
                except Exception:
                    pass
                # Return structured summary as trace output (not raw floats)
                return wav, elapsed, {
                    "duration_s":      round(duration, 3),
                    "sample_rate":     SNAC_SR,
                    "rtf":             round(rtf, 4),
                    "elapsed_s":       round(elapsed, 3),
                    "training_step":   step,
                }
            return wav, elapsed, {"error": "snac_decode returned None", "training_step": step}

        if _has_trace:
            try:
                with mlflow.start_span(name="orpheus_tts_pipeline", span_type="CHAIN") as root:
                    root.set_inputs({"text": text, "training_step": step})
                    result = _run(text)
                    wav, elapsed, summary = result
                    root.set_outputs(summary)
                return wav, elapsed
            except Exception:
                pass
        result = _run(text)
        return result[0], result[1]

    # ── Helper: WER / CER via Whisper (runs on CPU to avoid VRAM contention) ──
    def compute_wer_cer(whisper_mdl, wav: np.ndarray, reference: str):
        import jiwer
        result = whisper_mdl.transcribe(
            wav.astype(np.float32), language="tr", task="transcribe",
            initial_prompt="Türkçe konuşma.",   # nudge Whisper toward Turkish
        )
        hyp = result["text"].strip().lower()
        ref = reference.strip().lower()
        return jiwer.wer(ref, hyp), jiwer.cer(ref, hyp), hyp

    # ── Helper: UTMOS MOS predictor (CPU, loaded once) ────────────────────────
    def compute_utmos(utmos_mdl, wav: np.ndarray) -> float:
        import torchaudio
        t = torch.tensor(wav).unsqueeze(0)
        t16 = torchaudio.functional.resample(t, SNAC_SR, 16_000)
        return float(utmos_mdl.predict_from_wavs([t16])[0])

    # ── Helper: log audio batch + quality metrics to MLflow ───────────────────
    def log_audio_batch(model, tokenizer, snac_model, device, step: int, folder: str,
                        whisper_mdl=None, utmos_mdl=None, *, baseline: bool = False):
        model.eval()
        metrics = {}
        tmp = Path(tempfile.mkdtemp())

        wers, cers, utmos_scores, rtfs = [], [], [], []

        for label, text in EVAL_SENTENCES:
            wav, elapsed = generate_audio(
                model, tokenizer, snac_model, text, device, step=step, baseline=baseline,
            )
            if wav is None:
                log.warning(f"No audio for '{label}' at step {step}")
                continue

            duration = len(wav) / SNAC_SR
            if duration < 0.3:
                log.warning(f"Audio too short ({duration:.2f}s) for '{label}' at step {step} — skipping")
                continue

            wav = _clean_wav(wav)
            duration = len(wav) / SNAC_SR

            rtf = elapsed / max(duration, 1e-6)
            rtfs.append(rtf)
            metrics[f"rtf/{label}"] = rtf

            # WAV artifact
            wav_path = tmp / f"{label}.wav"
            sf.write(str(wav_path), wav, samplerate=SNAC_SR)
            mlflow.log_artifact(str(wav_path), artifact_path=f"{folder}/{label}")

            # Spectrogram
            fig, ax = plt.subplots(figsize=(10, 3))
            ax.specgram(wav, Fs=SNAC_SR, cmap="magma")
            ax.set_title(f"step {step:,} | {label}: {text[:60]}")
            ax.set_xlabel("Time (s)")
            ax.set_ylabel("Frequency (Hz)")
            fig.tight_layout()
            spec_path = tmp / f"{label}_spec.png"
            fig.savefig(str(spec_path), dpi=100)
            plt.close(fig)
            mlflow.log_artifact(str(spec_path), artifact_path=f"{folder}/{label}")

            # WER / CER (Whisper on CPU)
            if whisper_mdl is not None:
                try:
                    wer, cer, hyp = compute_wer_cer(whisper_mdl, wav, text)
                    wers.append(wer)
                    cers.append(cer)
                    metrics[f"wer/{label}"] = wer
                    metrics[f"cer/{label}"] = cer
                    log.info(f"  [{label}] WER={wer:.3f}  CER={cer:.3f}  hyp: {hyp[:60]}")
                except Exception as e:
                    log.warning(f"WER/CER failed for {label}: {e}")

            # UTMOS MOS
            if utmos_mdl is not None:
                try:
                    mos = compute_utmos(utmos_mdl, wav)
                    utmos_scores.append(mos)
                    metrics[f"utmos/{label}"] = mos
                except Exception as e:
                    log.warning(f"UTMOS failed for {label}: {e}")

        # Aggregate means
        if rtfs:
            metrics["rtf/mean"] = sum(rtfs) / len(rtfs)
        if wers:
            metrics["wer/mean"] = sum(wers) / len(wers)
        if cers:
            metrics["cer/mean"] = sum(cers) / len(cers)
        if utmos_scores:
            metrics["utmos/mean"] = sum(utmos_scores) / len(utmos_scores)

        mlflow.log_metrics(metrics, step=step)
        model.train()

    # ── MLflow callback ───────────────────────────────────────────────────────
    class MLflowAudioCallback(TrainerCallback):
        """
        Drives all custom MLflow logging:
          on_train_begin  → tags, dataset params, baseline audio (step 0)
          on_log          → perplexity alongside every loss report
          on_step_end     → audio + spectrogram every audio_log_steps
          on_train_end    → final audio, log model artifact, register
        """

        def __init__(self):
            self._snac    = None
            self._whisper = None
            self._utmos   = None
            self._device  = None

        def _get_snac(self):
            if self._snac is None:
                from snac import SNAC
                self._snac = (
                    SNAC.from_pretrained("hubertsiuzdak/snac_24khz", cache_dir=hf_cache)
                    .eval().to(self._device)
                )
            return self._snac

        def _get_whisper(self):
            if self._whisper is None:
                import whisper
                # Load on CPU — avoids VRAM contention with the training model
                self._whisper = whisper.load_model(whisper_model, device="cpu")
                log.info(f"Whisper-{whisper_model} loaded on CPU for in-training WER/CER")
            return self._whisper

        def _get_utmos(self):
            if self._utmos is None:
                try:
                    import utmos
                    self._utmos = utmos.Score(device="cpu")
                    log.info("UTMOS loaded on CPU for in-training MOS")
                except Exception as e:
                    log.warning(f"UTMOS unavailable: {e} — skipping MOS during training")
                    self._utmos = False   # sentinel: don't retry
            return self._utmos if self._utmos is not False else None

        def on_train_begin(self, args, state, control, model=None, **kwargs):
            self._device = next(model.parameters()).device
            if not state.is_world_process_zero:
                return
            # Active MLflow run guaranteed here — HF Trainer's MLflowCallback
            # runs before user callbacks and creates the run in its on_train_begin.
            world = int(os.environ.get("WORLD_SIZE", "1"))
            platform = os.environ.get(
                "MLFLOW_PLATFORM", "openshift-ai/kubeflow-trainer-v2"
            )
            mlflow.set_tags({
                "base_model":      base_model,
                "dataset":         hf_dataset,
                "train_samples":   str(max_samples or "full"),
                "max_seq_len":     str(max_seq_len),
                "n_gpus":          str(torch.cuda.device_count() * world),
                "gpu":             torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu",
                "effective_batch": str(batch_size * grad_accum * world),
                "platform":        platform,
            })
            # Log dataset stats now that a run is active
            if _dataset_params:
                mlflow.log_params(_dataset_params)
            mlflow.log_params({
                "lora_r": lora_r,
                "lora_alpha": lora_alpha,
                "lora_dropout": lora_dropout,
                "lora_target_modules": "q/k/v/o/gate/up/down_proj",
                "trainable_params_M": round(trainable / 1e6, 1),
                "total_params_B": round(total / 1e9, 2),
                "learning_rate": learning_rate,
                "num_epochs": num_epochs,
                "batch_size": batch_size,
                "grad_accum_steps": grad_accum,
                "eval_steps": effective_eval_steps,
                "audio_log_steps": audio_log_steps,
                "lr_scheduler": "cosine",
                "warmup_ratio": warmup_ratio,
                "weight_decay": 0.01,
                "eval_gen_temperature": GEN_TEMPERATURE,
                "eval_gen_top_p": GEN_TOP_P,
                "eval_gen_max_new_tokens": GEN_MAX_NEW_TOKENS,
                "eval_gen_min_new_tokens": GEN_MIN_NEW_TOKENS,
                "eval_gen_repetition_penalty": GEN_REPETITION_PENALTY,
                "eval_gen_trim_top_db": GEN_TRIM_TOP_DB,
            })

            log.info("Logging pretrained baseline audio + metrics …")
            try:
                log_audio_batch(
                    model, tokenizer, self._get_snac(), self._device,
                    step=0, folder="audio/step_000000/pretrained_baseline",
                    whisper_mdl=self._get_whisper(),
                    utmos_mdl=self._get_utmos(),
                    baseline=True,
                )
            except Exception as e:
                log.warning(f"Baseline audio failed: {e}")

        def on_log(self, args, state, control, logs=None, **kwargs):
            if not state.is_world_process_zero or not logs:
                return
            step = state.global_step
            for key, alias in (("loss", "train/loss"), ("eval_loss", "eval/loss")):
                if key in logs:
                    try:
                        v = logs[key]
                        mlflow.log_metric(alias, v, step=step)
                        mlflow.log_metric(
                            alias.replace("loss", "perplexity"),
                            math.exp(min(v, 10)),
                            step=step,
                        )
                    except Exception:
                        pass
            # Pass through learning_rate trend
            if "learning_rate" in logs:
                try:
                    mlflow.log_metric("train/lr", logs["learning_rate"], step=step)
                except Exception:
                    pass

        def on_step_end(self, args, state, control, model=None, **kwargs):
            if not state.is_world_process_zero:
                return
            if state.global_step > 0 and state.global_step % audio_log_steps == 0:
                log.info(f"Logging audio at step {state.global_step} …")
                try:
                    log_audio_batch(
                        model, tokenizer, self._get_snac(), self._device,
                        step=state.global_step,
                        folder=f"audio/step_{state.global_step:06d}/finetuned",
                        whisper_mdl=self._get_whisper(),
                        utmos_mdl=self._get_utmos(),
                    )
                except Exception as e:
                    log.warning(f"Audio at step {state.global_step} failed: {e}")

        def on_save(self, args, state, control, model=None, **kwargs):
            """Register a model version every time the trainer saves a checkpoint."""
            if not state.is_world_process_zero:
                return
            step = state.global_step
            ckpt_path = Path(args.output_dir) / f"checkpoint-{step}"
            try:
                # Log only lightweight metadata — weights stay on PVC
                for fname in ("config.json", "tokenizer_config.json",
                              "tokenizer.json", "special_tokens_map.json"):
                    p = ckpt_path / fname
                    if p.exists():
                        mlflow.log_artifact(
                            str(p),
                            artifact_path=f"checkpoints/step_{step:06d}",
                        )
                mlflow.set_tags({
                    f"ckpt_step_{step:06d}": str(ckpt_path),
                    "latest_checkpoint": str(ckpt_path),
                    "latest_checkpoint_step": str(step),
                })
                log.info(f"Checkpoint tagged in MLflow: step_{step:06d} → {ckpt_path}")
            except Exception as e:
                log.warning(f"Checkpoint registration failed at step {step}: {e}")

        def on_train_end(self, args, state, control, model=None, **kwargs):
            if not state.is_world_process_zero:
                return
            # Log final audio samples while run is still active
            try:
                log_audio_batch(
                    model, tokenizer, self._get_snac(), self._device,
                    step=state.global_step, folder="audio/final",
                    whisper_mdl=self._get_whisper(),
                    utmos_mdl=self._get_utmos(),
                )
            except Exception as e:
                log.warning(f"Final audio failed: {e}")
            # Final model save happens after trainer.train() returns.

    # ── Load tokenizer + model ────────────────────────────────────────────────
    log.info(f"Loading model: {base_model}")
    tokenizer = AutoTokenizer.from_pretrained(base_model, cache_dir=hf_cache)
    tokenizer.pad_token = tokenizer.eos_token

    try:
        from flash_attn import flash_attn_func  # noqa: F401
        attn_impl = "flash_attention_2"
    except ImportError:
        attn_impl = "sdpa"
        log.warning("flash-attn not available — falling back to SDPA")

    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        cache_dir=hf_cache,
        torch_dtype=torch.bfloat16,
        attn_implementation=attn_impl,
    )
    lora_cfg = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=lora_r,
        lora_alpha=lora_alpha,
        lora_dropout=lora_dropout,
        bias="none",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"],
    )
    model = get_peft_model(model, lora_cfg)
    model.enable_input_require_grads()
    trainable, total = model.get_nb_trainable_parameters()
    log.info(f"LoRA: {trainable/1e6:.1f}M trainable / {total/1e9:.2f}B total "
             f"({100*trainable/total:.2f}% of params)")

    # ── Load dataset (preprocessed by preprocess(), run on rank 0) ──────────────
    preprocessed_dir = Path(data_dir) if data_dir else Path(checkpoint_dir).parent / "preprocessed"
    if (preprocessed_dir / ".done").exists():
        log.info("Loading preprocessed dataset from %s", preprocessed_dir)
        ds = load_from_disk(str(preprocessed_dir))
    else:
        raise RuntimeError(
            f"Preprocessed dataset not found at {preprocessed_dir}. "
            "Ensure preprocess() ran on rank 0 before calling train()."
        )

    if max_samples:
        ds = ds.select(range(min(max_samples, len(ds))))

    def _audio_only_labels(example):
        """Mask prompt tokens so loss is computed on audio tokens only."""
        ids = example["input_ids"]
        try:
            sos_idx = ids.index(TOK_SOS)
        except ValueError:
            example["labels"] = list(ids)
            return example
        example["labels"] = [-100] * (sos_idx + 1) + ids[sos_idx + 1:]
        return example

    ds = ds.map(_audio_only_labels)

    before = len(ds)
    ds = ds.filter(lambda x: len(x["input_ids"]) <= max_seq_len)
    dropped = before - len(ds)

    if is_main:
        lengths = [len(x["input_ids"]) for x in ds]
        # Stored here; logged inside on_train_begin when the run is active
        _dataset_params.update({
            "dataset_samples": len(ds),
            "samples_dropped": dropped,
            "seq_len_mean":    round(np.mean(lengths)),
            "seq_len_p95":     round(np.percentile(lengths, 95)),
            "seq_len_max":     int(max(lengths)),
        })

    split    = ds.train_test_split(test_size=eval_split, seed=42)
    train_ds = split["train"]
    eval_ds  = split["test"]
    log.info(f"Train: {len(train_ds)}  Eval: {len(eval_ds)}  Dropped: {dropped}")

    # ── Trainer ───────────────────────────────────────────────────────────────
    collator = DataCollatorForSeq2Seq(
        tokenizer=tokenizer, model=model,
        padding="longest", pad_to_multiple_of=8,
        label_pad_token_id=-100,
    )

    training_args = TrainingArguments(
        output_dir=str(out_dir),
        num_train_epochs=num_epochs,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        gradient_accumulation_steps=grad_accum,
        gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False},
        learning_rate=learning_rate,
        lr_scheduler_type="cosine",
        warmup_ratio=warmup_ratio,
        weight_decay=0.01,
        bf16=True,
        tf32=True,
        logging_steps=logging_steps,
        eval_steps=effective_eval_steps,
        eval_strategy="steps",
        save_steps=save_steps,
        save_total_limit=3,
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        dataloader_num_workers=4,
        dataloader_pin_memory=True,
        remove_unused_columns=False,
        report_to="mlflow",
        run_name=f"orpheus-tr-{max_samples or 'full'}-b{batch_size}x{grad_accum}",
        ddp_find_unused_parameters=False,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        data_collator=collator,
        tokenizer=tokenizer,
        callbacks=[MLflowAudioCallback()],
    )

    log.info("Starting training …")
    trainer.train()

    if trainer.is_world_process_zero():
        final = out_dir / "final"
        trainer.save_model(str(final))
        tokenizer.save_pretrained(str(final))
        log.info(f"Model saved → {final}")

        # Log lightweight metadata files to MLflow (not the 6GB weights).
        # Full weights live on the PVC at checkpoint_dir/final — reference them via tag.
        meta_files = ["config.json", "tokenizer_config.json",
                      "tokenizer.json", "special_tokens_map.json"]
        for fname in meta_files:
            p = final / fname
            if p.exists():
                mlflow.log_artifact(str(p), artifact_path="model_metadata")

        mlflow.set_tag("checkpoint_path", str(final))

        mlflow.set_tags({
            "final_checkpoint_path": str(final),
            "stage": "final",
        })
        log.info(f"Final model tagged in MLflow: {final}")


# ── CLI entry point ───────────────────────────────────────────────────────────

def preprocess(
    raw_dataset: str = "afkfatih/turkish-tts-combined-raw",
    base_model:  str = "unsloth/orpheus-3b-0.1-pretrained",
    out_dir:     str = "/data/orpheus/preprocessed",
    hf_cache:    str = "/data/orpheus/hf-cache",
    max_seq_len: int = 4096,
    max_samples: int = 0,
    force:       bool = False,
):
    """
    Tokenise raw Turkish TTS audio into Orpheus token sequences and save to PVC.
    Invoked as: python train_orpheus.py --preprocess  (node 0 only, before torchrun)
    """
    import io
    import logging
    import math
    import os
    from pathlib import Path as _Path

    import numpy as np
    import soundfile as sf
    import torch
    from datasets import Audio, Dataset, load_dataset, load_from_disk
    from scipy.signal import resample_poly
    from snac import SNAC
    from transformers import AutoTokenizer

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    log = logging.getLogger("preprocess")

    # Token constants (must match train())
    LLAMA_VOCAB = 128_256
    CODE_OFFSET = LLAMA_VOCAB + 10
    SNAC_SR     = 24_000
    TOK_SOS, TOK_SOH, TOK_EOH = LLAMA_VOCAB+1, LLAMA_VOCAB+3, LLAMA_VOCAB+4
    TOK_SOA, TOK_EOA, TOK_EOT = LLAMA_VOCAB+5, LLAMA_VOCAB+6, LLAMA_VOCAB+9

    # ── Distributed shard setup ───────────────────────────────────────────────
    # Each Kubeflow node processes its slice; node 0 merges and writes sentinel.
    node_rank  = int(os.environ.get("PET_NODE_RANK", "0"))
    num_nodes  = int(os.environ.get("PET_NNODES",    "1"))

    out_path = _Path(out_dir)
    sentinel = out_path / ".done"
    if sentinel.exists() and not force:
        log.info("Already preprocessed at %s — skipping (node %d).", out_path, node_rank)
        return

    os.environ["HF_HOME"] = hf_cache
    device = "cuda" if torch.cuda.is_available() else "cpu"
    log.info("Node %d/%d — device: %s", node_rank, num_nodes, device)

    tokenizer  = AutoTokenizer.from_pretrained(base_model, cache_dir=hf_cache)
    snac_model = SNAC.from_pretrained("hubertsiuzdak/snac_24khz",
                                      cache_dir=hf_cache).to(device).eval()

    log.info("Loading raw dataset: %s …", raw_dataset)
    raw = load_dataset(raw_dataset, split="train", cache_dir=hf_cache)
    raw = raw.cast_column("audio", Audio(decode=False))  # skip torchcodec
    total = min(max_samples, len(raw)) if max_samples > 0 else len(raw)

    # Slice this node's share
    shard_size = (total + num_nodes - 1) // num_nodes
    start = node_rank * shard_size
    end   = min(start + shard_size, total)
    shard = raw.select(range(start, end))
    log.info("Node %d shard: samples %d–%d (%d total)", node_rank, start, end-1, len(shard))

    def _encode(wav_np, src_sr):
        if wav_np.ndim == 2:
            wav_np = wav_np.mean(axis=1)
        if src_sr != SNAC_SR:
            gcd = math.gcd(int(src_sr), SNAC_SR)
            wav_np = resample_poly(wav_np, SNAC_SR // gcd, src_sr // gcd).astype(np.float32)
        wav = torch.tensor(wav_np).unsqueeze(0).unsqueeze(0).to(device)
        with torch.inference_mode():
            codes = snac_model.encode(wav)
        return codes[0][0].tolist(), codes[1][0].tolist(), codes[2][0].tolist()

    def _interleave(l0, l1, l2):
        n = min(len(l0), len(l1)//2, len(l2)//4)
        t = []
        for f in range(n):
            t += [CODE_OFFSET+l0[f], CODE_OFFSET+4096+l1[2*f],
                  CODE_OFFSET+8192+l2[4*f], CODE_OFFSET+8192+l2[4*f+1],
                  CODE_OFFSET+4096+l1[2*f+1], CODE_OFFSET+8192+l2[4*f+2],
                  CODE_OFFSET+8192+l2[4*f+3]]
        return t

    out_path.mkdir(parents=True, exist_ok=True)
    rows, skipped = [], 0
    for i, sample in enumerate(shard):
        if i % 500 == 0:
            log.info("  node%d: %d / %d  (skipped %d)", node_rank, i, len(shard), skipped)
        try:
            text      = sample["text"].strip()
            audio     = sample["audio"]
            raw_bytes = audio.get("bytes") or open(audio["path"], "rb").read()
            wav, sr   = sf.read(io.BytesIO(raw_bytes), dtype="float32", always_2d=False)
            t_ids     = tokenizer.encode(text, add_special_tokens=False)
            l0, l1, l2 = _encode(wav, sr)
            seq = ([TOK_SOH] + t_ids + [TOK_EOT, TOK_EOH, TOK_SOA, TOK_SOS]
                   + _interleave(l0, l1, l2) + [TOK_EOA])
            if len(seq) > max_seq_len:
                skipped += 1
                continue
            sos_idx = seq.index(TOK_SOS)
            labels = [-100] * (sos_idx + 1) + seq[sos_idx + 1:]
            rows.append({
                "input_ids": seq,
                "labels": labels,
                "attention_mask": [1] * len(seq),
            })
        except Exception as e:
            log.warning("node%d sample %d skipped: %s", node_rank, i, e)
            skipped += 1

    log.info("node%d done: %d kept, %d skipped", node_rank, len(rows), skipped)

    # Save this node's shard and signal completion
    shard_path = out_path / f"shard_{node_rank}"
    Dataset.from_list(rows).save_to_disk(str(shard_path))
    (out_path / f".shard_{node_rank}.done").touch()
    log.info("node%d shard saved to %s", node_rank, shard_path)

    # Node 0 waits for all shards then merges
    if node_rank == 0:
        import time
        for rank in range(1, num_nodes):
            shard_sentinel = out_path / f".shard_{rank}.done"
            log.info("node0: waiting for node%d shard …", rank)
            while not shard_sentinel.exists():
                time.sleep(5)

        log.info("node0: merging %d shards …", num_nodes)
        from datasets import concatenate_datasets
        shards = [load_from_disk(str(out_path / f"shard_{r}")) for r in range(num_nodes)]
        merged = concatenate_datasets(shards)
        merged.save_to_disk(str(out_path))
        sentinel.touch()
        log.info("Merged %d sequences → %s", len(merged), out_path)


if __name__ == "__main__":
    import os  # noqa: E401
    import sys  # noqa: E401
    from pathlib import Path
    def _e(k, d, cast=str): return cast(os.environ.get(k, d))

    if "--preprocess" in sys.argv:
        preprocess(
            raw_dataset = _e("HF_DATASET",        "afkfatih/turkish-tts-combined-raw"),
            base_model  = _e("BASE_MODEL",         "unsloth/orpheus-3b-0.1-pretrained"),
            out_dir     = str(Path(_e("CHECKPOINT_DIR",
                              "/data/orpheus/checkpoints/turkish")).parent / "preprocessed"),
            hf_cache    = _e("HF_HOME",            "/data/orpheus/hf-cache"),
            max_seq_len = _e("MAX_SEQ_LEN",        4096, int),
            max_samples = _e("PREPROCESS_SAMPLES", _e("MAX_TRAIN_SAMPLES", "0"), int),
            force       = "--force" in sys.argv,
        )
        sys.exit(0)

    train(
        base_model        = _e("BASE_MODEL",       "unsloth/orpheus-3b-0.1-pretrained"),
        hf_dataset        = _e("HF_DATASET",       "afkfatih/turkish-tts-combined-raw"),
        checkpoint_dir    = _e("CHECKPOINT_DIR",   "/data/orpheus/checkpoints/turkish"),
        hf_cache          = _e("HF_HOME",          "/data/orpheus/hf-cache"),
        max_samples       = _e("MAX_TRAIN_SAMPLES", 0,     int),
        max_seq_len       = _e("MAX_SEQ_LEN",      4096,   int),
        batch_size        = _e("BATCH_SIZE",        2,     int),
        grad_accum        = _e("GRAD_ACCUM",        4,     int),
        learning_rate     = _e("LEARNING_RATE",     1e-4,  float),
        num_epochs        = _e("NUM_EPOCHS",        3,     int),
        save_steps        = _e("SAVE_STEPS",        200,   int),
        logging_steps     = _e("LOGGING_STEPS",     10,    int),
        eval_steps        = _e("EVAL_STEPS",        0,     int),
        audio_log_steps   = _e("AUDIO_LOG_STEPS",   100,   int),
        eval_split        = _e("EVAL_SPLIT",        0.05,  float),
        warmup_ratio      = _e("WARMUP_RATIO",      0.05,  float),
        lora_r            = _e("LORA_R",            16,    int),
        lora_alpha        = _e("LORA_ALPHA",        32,    int),
        lora_dropout      = _e("LORA_DROPOUT",      0.05,  float),
        mlflow_experiment = _e("MLFLOW_EXPERIMENT", "orpheus-turkish-tts"),
        whisper_model     = _e("WHISPER_MODEL",     "small"),
    )
