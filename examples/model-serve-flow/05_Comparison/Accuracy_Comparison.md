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
|arc_easy                               |      1|none  |     0|acc                    |↑  |0.8127|±  |0.0080|
|                                       |       |none  |     0|acc_norm               |↑  |0.7588|±  |0.0088|
|hellaswag                              |      1|none  |     0|acc                    |↑  |0.5742|±  |0.0049|
|                                       |       |none  |     0|acc_norm               |↑  |0.7254|±  |0.0045|
|ifeval                                 |      4|none  |     0|inst_level_loose_acc   |↑  |0.8513|±  |   N/A|
|                                       |       |none  |     0|inst_level_strict_acc  |↑  |0.8189|±  |   N/A|
|                                       |       |none  |     0|prompt_level_loose_acc |↑  |0.7874|±  |0.0176|
|                                       |       |none  |     0|prompt_level_strict_acc|↑  |0.7449|±  |0.0188|
|mmlu                                   |      2|none  |      |acc                    |↑  |0.6321|±  |0.0038|
| - humanities                          |      2|none  |      |acc                    |↑  |0.5868|±  |0.0068|
|  - formal_logic                       |      1|none  |     0|acc                    |↑  |0.5000|±  |0.0447|
|  - high_school_european_history       |      1|none  |     0|acc                    |↑  |0.7455|±  |0.0340|
|  - high_school_us_history             |      1|none  |     0|acc                    |↑  |0.7892|±  |0.0286|
|  - high_school_world_history          |      1|none  |     0|acc                    |↑  |0.8186|±  |0.0251|
|  - international_law                  |      1|none  |     0|acc                    |↑  |0.7686|±  |0.0385|
|  - jurisprudence                      |      1|none  |     0|acc                    |↑  |0.7315|±  |0.0428|
|  - logical_fallacies                  |      1|none  |     0|acc                    |↑  |0.7730|±  |0.0329|
|  - moral_disputes                     |      1|none  |     0|acc                    |↑  |0.6792|±  |0.0251|
|  - moral_scenarios                    |      1|none  |     0|acc                    |↑  |0.4190|±  |0.0165|
|  - philosophy                         |      1|none  |     0|acc                    |↑  |0.6977|±  |0.0261|
|  - prehistory                         |      1|none  |     0|acc                    |↑  |0.7130|±  |0.0252|
|  - professional_law                   |      1|none  |     0|acc                    |↑  |0.4687|±  |0.0127|
|  - world_religions                    |      1|none  |     0|acc                    |↑  |0.8480|±  |0.0275|
| - other                               |      2|none  |      |acc                    |↑  |0.7177|±  |0.0078|
|  - business_ethics                    |      1|none  |     0|acc                    |↑  |0.6500|±  |0.0479|
|  - clinical_knowledge                 |      1|none  |     0|acc                    |↑  |0.7094|±  |0.0279|
|  - college_medicine                   |      1|none  |     0|acc                    |↑  |0.6416|±  |0.0366|
|  - global_facts                       |      1|none  |     0|acc                    |↑  |0.4200|±  |0.0496|
|  - human_aging                        |      1|none  |     0|acc                    |↑  |0.6771|±  |0.0314|
|  - management                         |      1|none  |     0|acc                    |↑  |0.8058|±  |0.0392|
|  - marketing                          |      1|none  |     0|acc                    |↑  |0.8547|±  |0.0231|
|  - medical_genetics                   |      1|none  |     0|acc                    |↑  |0.8000|±  |0.0402|
|  - miscellaneous                      |      1|none  |     0|acc                    |↑  |0.8084|±  |0.0141|
|  - nutrition                          |      1|none  |     0|acc                    |↑  |0.7516|±  |0.0247|
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
| - stem                                |      2|none  |      |acc                    |↑  |0.5059|±  |0.0084|
|  - abstract_algebra                   |      1|none  |     0|acc                    |↑  |0.2700|±  |0.0446|
|  - anatomy                            |      1|none  |     0|acc                    |↑  |0.6222|±  |0.0419|
|  - astronomy                          |      1|none  |     0|acc                    |↑  |0.7039|±  |0.0372|
|  - college_biology                    |      1|none  |     0|acc                    |↑  |0.7639|±  |0.0355|
|  - college_chemistry                  |      1|none  |     0|acc                    |↑  |0.4700|±  |0.0502|
|  - college_computer_science           |      1|none  |     0|acc                    |↑  |0.4100|±  |0.0494|
|  - college_mathematics                |      1|none  |     0|acc                    |↑  |0.2800|±  |0.0451|
|  - college_physics                    |      1|none  |     0|acc                    |↑  |0.3824|±  |0.0484|
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
|arc_easy                               |      1|none  |     0|acc                    |↑  |0.8114|±  |0.0080|
|                                       |       |none  |     0|acc_norm               |↑  |0.7584|±  |0.0088|
|hellaswag                              |      1|none  |     0|acc                    |↑  |0.5756|±  |0.0049|
|                                       |       |none  |     0|acc_norm               |↑  |0.7261|±  |0.0045|
|ifeval                                 |      4|none  |     0|inst_level_loose_acc   |↑  |0.8609|±  |   N/A|
|                                       |       |none  |     0|inst_level_strict_acc  |↑  |0.8225|±  |   N/A|
|                                       |       |none  |     0|prompt_level_loose_acc |↑  |0.8004|±  |0.0172|
|                                       |       |none  |     0|prompt_level_strict_acc|↑  |0.7468|±  |0.0187|
|mmlu                                   |      2|none  |      |acc                    |↑  |0.6322|±  |0.0038|
| - humanities                          |      2|none  |      |acc                    |↑  |0.5853|±  |0.0068|
|  - formal_logic                       |      1|none  |     0|acc                    |↑  |0.4683|±  |0.0446|
|  - high_school_european_history       |      1|none  |     0|acc                    |↑  |0.7455|±  |0.0340|
|  - high_school_us_history             |      1|none  |     0|acc                    |↑  |0.7892|±  |0.0286|
|  - high_school_world_history          |      1|none  |     0|acc                    |↑  |0.8101|±  |0.0255|
|  - international_law                  |      1|none  |     0|acc                    |↑  |0.7686|±  |0.0385|
|  - jurisprudence                      |      1|none  |     0|acc                    |↑  |0.7315|±  |0.0428|
|  - logical_fallacies                  |      1|none  |     0|acc                    |↑  |0.7730|±  |0.0329|
|  - moral_disputes                     |      1|none  |     0|acc                    |↑  |0.6792|±  |0.0251|
|  - moral_scenarios                    |      1|none  |     0|acc                    |↑  |0.4145|±  |0.0165|
|  - philosophy                         |      1|none  |     0|acc                    |↑  |0.6945|±  |0.0262|
|  - prehistory                         |      1|none  |     0|acc                    |↑  |0.7130|±  |0.0252|
|  - professional_law                   |      1|none  |     0|acc                    |↑  |0.4713|±  |0.0127|
|  - world_religions                    |      1|none  |     0|acc                    |↑  |0.8480|±  |0.0275|
| - other                               |      2|none  |      |acc                    |↑  |0.7181|±  |0.0078|
|  - business_ethics                    |      1|none  |     0|acc                    |↑  |0.6600|±  |0.0476|
|  - clinical_knowledge                 |      1|none  |     0|acc                    |↑  |0.7019|±  |0.0282|
|  - college_medicine                   |      1|none  |     0|acc                    |↑  |0.6358|±  |0.0367|
|  - global_facts                       |      1|none  |     0|acc                    |↑  |0.4200|±  |0.0496|
|  - human_aging                        |      1|none  |     0|acc                    |↑  |0.6771|±  |0.0314|
|  - management                         |      1|none  |     0|acc                    |↑  |0.7961|±  |0.0399|
|  - marketing                          |      1|none  |     0|acc                    |↑  |0.8547|±  |0.0231|
|  - medical_genetics                   |      1|none  |     0|acc                    |↑  |0.7800|±  |0.0416|
|  - miscellaneous                      |      1|none  |     0|acc                    |↑  |0.8110|±  |0.0140|
|  - nutrition                          |      1|none  |     0|acc                    |↑  |0.7614|±  |0.0244|
|  - professional_accounting            |      1|none  |     0|acc                    |↑  |0.5284|±  |0.0298|
|  - professional_medicine              |      1|none  |     0|acc                    |↑  |0.7463|±  |0.0264|
|  - virology                           |      1|none  |     0|acc                    |↑  |0.5783|±  |0.0384|
| - social sciences                     |      2|none  |      |acc                    |↑  |0.7452|±  |0.0077|
|  - econometrics                       |      1|none  |     0|acc                    |↑  |0.4561|±  |0.0469|
|  - high_school_geography              |      1|none  |     0|acc                    |↑  |0.7980|±  |0.0286|
|  - high_school_government_and_politics|      1|none  |     0|acc                    |↑  |0.8549|±  |0.0254|
|  - high_school_macroeconomics         |      1|none  |     0|acc                    |↑  |0.6538|±  |0.0241|
|  - high_school_microeconomics         |      1|none  |     0|acc                    |↑  |0.7395|±  |0.0285|
|  - high_school_psychology             |      1|none  |     0|acc                    |↑  |0.8569|±  |0.0150|
|  - human_sexuality                    |      1|none  |     0|acc                    |↑  |0.7557|±  |0.0377|
|  - professional_psychology            |      1|none  |     0|acc                    |↑  |0.6846|±  |0.0188|
|  - public_relations                   |      1|none  |     0|acc                    |↑  |0.7000|±  |0.0439|
|  - security_studies                   |      1|none  |     0|acc                    |↑  |0.6939|±  |0.0295|
|  - sociology                          |      1|none  |     0|acc                    |↑  |0.8358|±  |0.0262|
|  - us_foreign_policy                  |      1|none  |     0|acc                    |↑  |0.8700|±  |0.0338|
| - stem                                |      2|none  |      |acc                    |↑  |0.5075|±  |0.0084|
|  - abstract_algebra                   |      1|none  |     0|acc                    |↑  |0.2700|±  |0.0446|
|  - anatomy                            |      1|none  |     0|acc                    |↑  |0.6222|±  |0.0419|
|  - astronomy                          |      1|none  |     0|acc                    |↑  |0.6974|±  |0.0374|
|  - college_biology                    |      1|none  |     0|acc                    |↑  |0.7639|±  |0.0355|
|  - college_chemistry                  |      1|none  |     0|acc                    |↑  |0.4600|±  |0.0501|
|  - college_computer_science           |      1|none  |     0|acc                    |↑  |0.4100|±  |0.0494|
|  - college_mathematics                |      1|none  |     0|acc                    |↑  |0.2600|±  |0.0441|
|  - college_physics                    |      1|none  |     0|acc                    |↑  |0.4118|±  |0.0490|
|  - computer_security                  |      1|none  |     0|acc                    |↑  |0.7200|±  |0.0451|
|  - conceptual_physics                 |      1|none  |     0|acc                    |↑  |0.6043|±  |0.0320|
|  - electrical_engineering             |      1|none  |     0|acc                    |↑  |0.5793|±  |0.0411|
|  - elementary_mathematics             |      1|none  |     0|acc                    |↑  |0.3968|±  |0.0252|
|  - high_school_biology                |      1|none  |     0|acc                    |↑  |0.7645|±  |0.0241|
|  - high_school_chemistry              |      1|none  |     0|acc                    |↑  |0.5074|±  |0.0352|
|  - high_school_computer_science       |      1|none  |     0|acc                    |↑  |0.6200|±  |0.0488|
|  - high_school_mathematics            |      1|none  |     0|acc                    |↑  |0.2519|±  |0.0265|
|  - high_school_physics                |      1|none  |     0|acc                    |↑  |0.3841|±  |0.0397|
|  - high_school_statistics             |      1|none  |     0|acc                    |↑  |0.4167|±  |0.0336|
|  - machine_learning                   |      1|none  |     0|acc                    |↑  |0.4643|±  |0.0473|
```

## Observation

Comparing the accuracies of the base and compressed models shows that the compressed model performs very similarly to the base model across most tasks. While there are small variations in some task-level metrics, the overall accuracy drop is minimal, demonstrating that compression (e.g., quantization to 8-bit) maintains the model’s capabilities effectively.

This indicates that the compressed model is suitable for deployment scenarios where reduced memory footprint and faster inference are required, without significantly sacrificing performance.
