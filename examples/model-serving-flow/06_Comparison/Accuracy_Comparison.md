## Goal

This document will compare the accuracy of the compressed and base models. Once the model is quantized/compressed, there is some level of quantization error introduced. It is important to evaluate the model's accuracy to ensure it performs well on standard benchmark tasks.

## Hardware

Single L40S GPU, 46GB

## Base Model

LLama-3.1-8B-Instruct

## Quantized Model

LLama_3.1_B_Instruct_int8-dynamic

## Quantization Scheme

Int W8A8

## Accuracy Results for Base Model

```text
|                 Tasks                 |Version|Filter|n-shot|        Metric         |   |Value |   |Stderr|
|---------------------------------------|------:|------|-----:|-----------------------|---|-----:|---|------|
|arc_easy                               |      1|none  |     0|acc                    |↑  |0.8136|±  |0.0080|
|                                       |       |none  |     0|acc_norm               |↑  |0.7588|±  |0.0088|
|hellaswag                              |      1|none  |     0|acc                    |↑  |0.5741|±  |0.0049|
|                                       |       |none  |     0|acc_norm               |↑  |0.7251|±  |0.0045|
|ifeval                                 |      4|none  |     0|inst_level_loose_acc   |↑  |0.8513|±  |   N/A|
|                                       |       |none  |     0|inst_level_strict_acc  |↑  |0.8189|±  |   N/A|
|                                       |       |none  |     0|prompt_level_loose_acc |↑  |0.7874|±  |0.0176|
|                                       |       |none  |     0|prompt_level_strict_acc|↑  |0.7449|±  |0.0188|
|mmlu                                   |      2|none  |      |acc                    |↑  |0.6322|±  |0.0038|
| - humanities                          |      2|none  |      |acc                    |↑  |0.5864|±  |0.0068|
|  - formal_logic                       |      1|none  |     0|acc                    |↑  |0.4921|±  |0.0447|
|  - high_school_european_history       |      1|none  |     0|acc                    |↑  |0.7455|±  |0.0340|
|  - high_school_us_history             |      1|none  |     0|acc                    |↑  |0.7892|±  |0.0286|
|  - high_school_world_history          |      1|none  |     0|acc                    |↑  |0.8186|±  |0.0251|
|  - international_law                  |      1|none  |     0|acc                    |↑  |0.7686|±  |0.0385|
|  - jurisprudence                      |      1|none  |     0|acc                    |↑  |0.7315|±  |0.0428|
|  - logical_fallacies                  |      1|none  |     0|acc                    |↑  |0.7730|±  |0.0329|
|  - moral_disputes                     |      1|none  |     0|acc                    |↑  |0.6792|±  |0.0251|
|  - moral_scenarios                    |      1|none  |     0|acc                    |↑  |0.4179|±  |0.0165|
|  - philosophy                         |      1|none  |     0|acc                    |↑  |0.6977|±  |0.0261|
|  - prehistory                         |      1|none  |     0|acc                    |↑  |0.7130|±  |0.0252|
|  - professional_law                   |      1|none  |     0|acc                    |↑  |0.4687|±  |0.0127|
|  - world_religions                    |      1|none  |     0|acc                    |↑  |0.8480|±  |0.0275|
| - other                               |      2|none  |      |acc                    |↑  |0.7184|±  |0.0078|
|  - business_ethics                    |      1|none  |     0|acc                    |↑  |0.6500|±  |0.0479|
|  - clinical_knowledge                 |      1|none  |     0|acc                    |↑  |0.7094|±  |0.0279|
|  - college_medicine                   |      1|none  |     0|acc                    |↑  |0.6416|±  |0.0366|
|  - global_facts                       |      1|none  |     0|acc                    |↑  |0.4200|±  |0.0496|
|  - human_aging                        |      1|none  |     0|acc                    |↑  |0.6771|±  |0.0314|
|  - management                         |      1|none  |     0|acc                    |↑  |0.8058|±  |0.0392|
|  - marketing                          |      1|none  |     0|acc                    |↑  |0.8547|±  |0.0231|
|  - medical_genetics                   |      1|none  |     0|acc                    |↑  |0.8100|±  |0.0394|
|  - miscellaneous                      |      1|none  |     0|acc                    |↑  |0.8084|±  |0.0141|
|  - nutrition                          |      1|none  |     0|acc                    |↑  |0.7549|±  |0.0246|
|  - professional_accounting            |      1|none  |     0|acc                    |↑  |0.5177|±  |0.0298|
|  - professional_medicine              |      1|none  |     0|acc                    |↑  |0.7610|±  |0.0259|
|  - virology                           |      1|none  |     0|acc                    |↑  |0.5663|±  |0.0386|
| - social sciences                     |      2|none  |      |acc                    |↑  |0.7442|±  |0.0077|
|  - econometrics                       |      1|none  |     0|acc                    |↑  |0.4386|±  |0.0467|
|  - high_school_geography              |      1|none  |     0|acc                    |↑  |0.7929|±  |0.0289|
|  - high_school_government_and_politics|      1|none  |     0|acc                    |↑  |0.8497|±  |0.0258|
|  - high_school_macroeconomics         |      1|none  |     0|acc                    |↑  |0.6564|±  |0.0241|
|  - high_school_microeconomics         |      1|none  |     0|acc                    |↑  |0.7479|±  |0.0282|
|  - high_school_psychology             |      1|none  |     0|acc                    |↑  |0.8642|±  |0.0147|
|  - human_sexuality                    |      1|none  |     0|acc                    |↑  |0.7634|±  |0.0373|
|  - professional_psychology            |      1|none  |     0|acc                    |↑  |0.6797|±  |0.0189|
|  - public_relations                   |      1|none  |     0|acc                    |↑  |0.6909|±  |0.0443|
|  - security_studies                   |      1|none  |     0|acc                    |↑  |0.6898|±  |0.0296|
|  - sociology                          |      1|none  |     0|acc                    |↑  |0.8308|±  |0.0265|
|  - us_foreign_policy                  |      1|none  |     0|acc                    |↑  |0.8600|±  |0.0349|
| - stem                                |      2|none  |      |acc                    |↑  |0.5062|±  |0.0084|
|  - abstract_algebra                   |      1|none  |     0|acc                    |↑  |0.2700|±  |0.0446|
|  - anatomy                            |      1|none  |     0|acc                    |↑  |0.6222|±  |0.0419|
|  - astronomy                          |      1|none  |     0|acc                    |↑  |0.6974|±  |0.0374|
|  - college_biology                    |      1|none  |     0|acc                    |↑  |0.7708|±  |0.0351|
|  - college_chemistry                  |      1|none  |     0|acc                    |↑  |0.4700|±  |0.0502|
|  - college_computer_science           |      1|none  |     0|acc                    |↑  |0.4100|±  |0.0494|
|  - college_mathematics                |      1|none  |     0|acc                    |↑  |0.2800|±  |0.0451|
|  - college_physics                    |      1|none  |     0|acc                    |↑  |0.3922|±  |0.0486|
|  - computer_security                  |      1|none  |     0|acc                    |↑  |0.7200|±  |0.0451|
|  - conceptual_physics                 |      1|none  |     0|acc                    |↑  |0.5915|±  |0.0321|
|  - electrical_engineering             |      1|none  |     0|acc                    |↑  |0.5724|±  |0.0412|
|  - elementary_mathematics             |      1|none  |     0|acc                    |↑  |0.3942|±  |0.0252|
|  - high_school_biology                |      1|none  |     0|acc                    |↑  |0.7581|±  |0.0244|
|  - high_school_chemistry              |      1|none  |     0|acc                    |↑  |0.5123|±  |0.0352|
|  - high_school_computer_science       |      1|none  |     0|acc                    |↑  |0.6100|±  |0.0490|
|  - high_school_mathematics            |      1|none  |     0|acc                    |↑  |0.2481|±  |0.0263|
|  - high_school_physics                |      1|none  |     0|acc                    |↑  |0.3709|±  |0.0394|
|  - high_school_statistics             |      1|none  |     0|acc                    |↑  |0.4213|±  |0.0337|
|  - machine_learning                   |      1|none  |     0|acc                    |↑  |0.4911|±  |0.0475|
```

## Accuracy Results for Compressed  Model

```text
|                 Tasks                 |Version|Filter|n-shot|        Metric         |   |Value |   |Stderr|
|---------------------------------------|------:|------|-----:|-----------------------|---|-----:|---|------|
|arc_easy                               |      1|none  |     0|acc                    |↑  |0.8106|±  |0.0080|
|                                       |       |none  |     0|acc_norm               |↑  |0.7555|±  |0.0088|
|hellaswag                              |      1|none  |     0|acc                    |↑  |0.5734|±  |0.0049|
|                                       |       |none  |     0|acc_norm               |↑  |0.7277|±  |0.0044|
|ifeval                                 |      4|none  |     0|inst_level_loose_acc   |↑  |0.8549|±  |   N/A|
|                                       |       |none  |     0|inst_level_strict_acc  |↑  |0.8237|±  |   N/A|
|                                       |       |none  |     0|prompt_level_loose_acc |↑  |0.7893|±  |0.0175|
|                                       |       |none  |     0|prompt_level_strict_acc|↑  |0.7449|±  |0.0188|
|mmlu                                   |      2|none  |      |acc                    |↑  |0.6311|±  |0.0038|
| - humanities                          |      2|none  |      |acc                    |↑  |0.5911|±  |0.0068|
|  - formal_logic                       |      1|none  |     0|acc                    |↑  |0.4921|±  |0.0447|
|  - high_school_european_history       |      1|none  |     0|acc                    |↑  |0.7697|±  |0.0329|
|  - high_school_us_history             |      1|none  |     0|acc                    |↑  |0.7990|±  |0.0281|
|  - high_school_world_history          |      1|none  |     0|acc                    |↑  |0.8186|±  |0.0251|
|  - international_law                  |      1|none  |     0|acc                    |↑  |0.7686|±  |0.0385|
|  - jurisprudence                      |      1|none  |     0|acc                    |↑  |0.7500|±  |0.0419|
|  - logical_fallacies                  |      1|none  |     0|acc                    |↑  |0.7669|±  |0.0332|
|  - moral_disputes                     |      1|none  |     0|acc                    |↑  |0.6792|±  |0.0251|
|  - moral_scenarios                    |      1|none  |     0|acc                    |↑  |0.4369|±  |0.0166|
|  - philosophy                         |      1|none  |     0|acc                    |↑  |0.6913|±  |0.0262|
|  - prehistory                         |      1|none  |     0|acc                    |↑  |0.7191|±  |0.0250|
|  - professional_law                   |      1|none  |     0|acc                    |↑  |0.4687|±  |0.0127|
|  - world_religions                    |      1|none  |     0|acc                    |↑  |0.8363|±  |0.0284|
| - other                               |      2|none  |      |acc                    |↑  |0.7132|±  |0.0079|
|  - business_ethics                    |      1|none  |     0|acc                    |↑  |0.6500|±  |0.0479|
|  - clinical_knowledge                 |      1|none  |     0|acc                    |↑  |0.7019|±  |0.0282|
|  - college_medicine                   |      1|none  |     0|acc                    |↑  |0.6474|±  |0.0364|
|  - global_facts                       |      1|none  |     0|acc                    |↑  |0.4100|±  |0.0494|
|  - human_aging                        |      1|none  |     0|acc                    |↑  |0.6861|±  |0.0311|
|  - management                         |      1|none  |     0|acc                    |↑  |0.7864|±  |0.0406|
|  - marketing                          |      1|none  |     0|acc                    |↑  |0.8462|±  |0.0236|
|  - medical_genetics                   |      1|none  |     0|acc                    |↑  |0.7700|±  |0.0423|
|  - miscellaneous                      |      1|none  |     0|acc                    |↑  |0.8059|±  |0.0141|
|  - nutrition                          |      1|none  |     0|acc                    |↑  |0.7614|±  |0.0244|
|  - professional_accounting            |      1|none  |     0|acc                    |↑  |0.4965|±  |0.0298|
|  - professional_medicine              |      1|none  |     0|acc                    |↑  |0.7721|±  |0.0255|
|  - virology                           |      1|none  |     0|acc                    |↑  |0.5361|±  |0.0388|
| - social sciences                     |      2|none  |      |acc                    |↑  |0.7394|±  |0.0077|
|  - econometrics                       |      1|none  |     0|acc                    |↑  |0.4474|±  |0.0468|
|  - high_school_geography              |      1|none  |     0|acc                    |↑  |0.7778|±  |0.0296|
|  - high_school_government_and_politics|      1|none  |     0|acc                    |↑  |0.8187|±  |0.0278|
|  - high_school_macroeconomics         |      1|none  |     0|acc                    |↑  |0.6487|±  |0.0242|
|  - high_school_microeconomics         |      1|none  |     0|acc                    |↑  |0.7437|±  |0.0284|
|  - high_school_psychology             |      1|none  |     0|acc                    |↑  |0.8606|±  |0.0149|
|  - human_sexuality                    |      1|none  |     0|acc                    |↑  |0.7634|±  |0.0373|
|  - professional_psychology            |      1|none  |     0|acc                    |↑  |0.6814|±  |0.0189|
|  - public_relations                   |      1|none  |     0|acc                    |↑  |0.6636|±  |0.0453|
|  - security_studies                   |      1|none  |     0|acc                    |↑  |0.6857|±  |0.0297|
|  - sociology                          |      1|none  |     0|acc                    |↑  |0.8408|±  |0.0259|
|  - us_foreign_policy                  |      1|none  |     0|acc                    |↑  |0.8600|±  |0.0349|
| - stem                                |      2|none  |      |acc                    |↑  |0.5043|±  |0.0084|
|  - abstract_algebra                   |      1|none  |     0|acc                    |↑  |0.2500|±  |0.0435|
|  - anatomy                            |      1|none  |     0|acc                    |↑  |0.6444|±  |0.0414|
|  - astronomy                          |      1|none  |     0|acc                    |↑  |0.6842|±  |0.0378|
|  - college_biology                    |      1|none  |     0|acc                    |↑  |0.7431|±  |0.0365|
|  - college_chemistry                  |      1|none  |     0|acc                    |↑  |0.4500|±  |0.0500|
|  - college_computer_science           |      1|none  |     0|acc                    |↑  |0.4200|±  |0.0496|
|  - college_mathematics                |      1|none  |     0|acc                    |↑  |0.2700|±  |0.0446|
|  - college_physics                    |      1|none  |     0|acc                    |↑  |0.3824|±  |0.0484|
|  - computer_security                  |      1|none  |     0|acc                    |↑  |0.7300|±  |0.0446|
|  - conceptual_physics                 |      1|none  |     0|acc                    |↑  |0.6000|±  |0.0320|
|  - electrical_engineering             |      1|none  |     0|acc                    |↑  |0.6069|±  |0.0407|
|  - elementary_mathematics             |      1|none  |     0|acc                    |↑  |0.4048|±  |0.0253|
|  - high_school_biology                |      1|none  |     0|acc                    |↑  |0.7774|±  |0.0237|
|  - high_school_chemistry              |      1|none  |     0|acc                    |↑  |0.4729|±  |0.0351|
|  - high_school_computer_science       |      1|none  |     0|acc                    |↑  |0.5800|±  |0.0496|
|  - high_school_mathematics            |      1|none  |     0|acc                    |↑  |0.2519|±  |0.0265|
|  - high_school_physics                |      1|none  |     0|acc                    |↑  |0.3444|±  |0.0388|
|  - high_school_statistics             |      1|none  |     0|acc                    |↑  |0.4213|±  |0.0337|
|  - machine_learning                   |      1|none  |     0|acc                    |↑  |0.4732|±  |0.0474|
```

## Observation

Comparing the accuracies of the base and compressed models shows that the compressed model performs very similarly to the base model across most tasks. While there are small variations in some task-level metrics, the overall accuracy drop is minimal, demonstrating that compression (e.g., quantization to 8-bit) maintains the model’s capabilities effectively.

This indicates that the compressed model is suitable for deployment scenarios where reduced memory footprint and faster inference are required, without significantly sacrificing performance.
