import os

import mlflow
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))


def print_eval_results(results, scorer_name, eval_experiment_id):
    """Print per-trace results with rationale from evaluation run assessments."""
    print("Metrics:", results.metrics)
    if results.result_df is None:
        return

    eval_traces = mlflow.search_traces(
        experiment_ids=[eval_experiment_id],
        filter_string=f"metadata.mlflow.sourceRun = '{results.run_id}'",
        return_type="list",
    )

    print("\nPer-trace results:")
    for _, row in results.result_df.iterrows():
        value = row.get(f"{scorer_name}/value", "N/A")
        request_raw = row.get("request", "")
        if isinstance(request_raw, dict) and "messages" in request_raw:
            msgs = request_raw["messages"]
            request = (
                msgs[-1].get("content", str(msgs[-1])) if msgs else str(request_raw)
            )
        else:
            request = str(request_raw)
        response = str(row.get("response", ""))[:100]
        print(f"  Verdict: {value}")
        print(f"  Request: {request[:100]}")
        print(f"  Response: {response}")

        trace_id = row.get("trace_id", "")
        for et in eval_traces:
            if et.info.trace_id == trace_id:
                for a in et.info.assessments:
                    if a.name == scorer_name and a.rationale:
                        print(f"  Rationale: {a.rationale}")
                        break
                break
        print()
