# InstructLab Multi-Phase Training Configurations

This directory contains hardware-specific configurations for running the LAB multi-phase training pipeline with different GPU setups.

## Quick Start

See [`lab_multiphase_configs.ipynb`](./lab_multiphase_configs.ipynb) for optimized training parameters for various hardware configurations including:

- **H200**: 1x, 2x, 4x, 8x GPU configurations
- **H100**: 2x, 4x, 8x GPU configurations  
- **A100 80GB**: 2x, 4x, 8x GPU configurations
- **A100 40GB**: 2x, 4x, 8x GPU configurations
- **L40S**: 4x, 8x GPU configurations
- **L4**: 8x GPU configurations

Each configuration includes memory-optimized settings for `max_tokens_per_gpu`, `max_seq_len`, `nproc_per_node`, and FSDP CPU offloading parameters.

Note: The values are all set assuming a single node with the above GPU resources. For multi-node, note that the default sharding strategy is FSDP [HYBRID_SHARD](https://docs.pytorch.org/docs/stable/fsdp.html#torch.distributed.fsdp.ShardingStrategy). Begin with the cooresponding settings that align with one of your given nodes, or switch to `FULL_SHARD` if required due to memory constraints.
