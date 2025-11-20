# Setup

## Navigation

- Overview - [Knowledge Tuning Overview](../README.md)
- Setup
- Module 01 - [Base Model Evaluation](../01_Base_Model_Evaluation/01_Base_Model_Evaluation_README.md)
- Module 02 - [Data Processing](../02_Data_Processing/02_Data_Processing_README.md)
- Module 03 - [Knowledge Generation](../03_Knowledge_Generation/03_Knowledge_Generation_README.md)
- Module 04 - [Knowledge Mixing](../04_Knowledge_Mixing/04_Knowledge_Mixing_README.md)
- Module 05 - [Model Training](../05_Model_Training/05_Model_Training_README.md)
- Module 06 - [Evaluation](../06_Evaluation/06_Evaluation_README.md)

## Set up your working environment

To use the Knowledge Tuning example, follow these steps to set up your working environment on your Red Hat OpenShift AI cluster:

1. [Configure resources on the OpenShift cluster](#configure-resources-on-the-openshift-cluster)
2. [Create a project](#create-a-project)
3. [Create a workbench](#create-a-workbench)
4. [Clone the example Git repository](#clone-the-example-git-repository)

For this example, you create an OpenShift project and a workbench. From the workench, you launch an JupyterLab integrated development environment. In JupyterLab, you run the provided notebooks that guide you through the example data processing, knowledge generation and mixing, model training, and evaluation workflow.

## Configure resources on the OpenShift cluster

The notebooks provided in the Knowledge Tuning example require the following resources:

- **GPUs:** GPUs are optional for the preprocessing and mixing steps. For the model training step, fine-tuning large models requires at least one NVIDIA A100/40GB or similar. Training smaller student models requires 8–16 GB GPU.

- **Persistent Volumes:** Attach a persistent volume with at least 200 GB.

To run all of the notebooks in the Knowledge Training example, you must ensure that the following resources are configured on the OpenShift cluster:

1. Your Red Hat OpenShift cluster administrator must configure the following resources:

   - A persistent volume with a storage capacity of 200 GB or greater.

   - Installed and enabled a NVIDIA GPU as described in [Enabling accelerators]https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.0/html/working_with_accelerators/enabling-accelerators_accelerators.

2. An OpenShift AI administrator must create a hardware profile that allocates the following resources, as described in [Creating a hardware profile](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.0/html/working_with_accelerators/working-with-hardware-profiles_accelerators#creating-a-hardware-profile_accelerators).

   - **CPU:**
     - Request: 100 Cores
     - Limit: 100 Cores
   - **Memory:**
     - Request: 100 GiB
     - Limit: 100 GiB
   - **Nvidia GPU**
     - Request: 1
     - Limit: 1

## Create a project

To implement an AI workflow in OpenShift AI, you must create a project. Projects help your team to organize and work together on resources within separated namespaces. From a project you can create many workbenches, each with their own IDE environment (for example, JupyterLab), and each with their own connections and cluster storage.

### Prerequisites

- You have logged in to Red Hat OpenShift AI.

### Procedure

1. On the navigation menu, select **Projects**. This page lists any existing projects that you have access to.

2. Click **Create project**.

3. In the **Create project** modal, enter a display name and description.

4. Click **Create**.

### Verification

You can see your project's initial state.

## Create a workbench

A workbench is an instance of your development and experimentation environment. When you create a workbench, you select a workbench image that has the tools, libraries, and an integrated development environment, such as JupyetrLab, that you need for developing AI models.

The JupyterLab environment is a web-based environment, but everything you do inside it happens on Red Hat OpenShift AI and is powered by the OpenShift cluster. This means that, without having to install and maintain anything on your own computer, and without using valuable local resources such as CPU, GPU and RAM, you can conduct your work in this powerful and stable managed environment.

### Prerequisites

- You created a project.

### Procedure

1. Navigate to the project detail page for the project that you created in *Create a project*.

2. Click the **Workbenches** tab, and then click **Create workbench**.

3. Fill out the name and description.

   Red Hat OpenShift AI provides several supported workbench images. In the **Workbench image** section, you can select one of the default images or a custom image that an administrator has set up for you. The **Jupyter | Minimal | CUDA | Python 3.12** has the libraries needed for this example.

4. Select the latest **Jupyter | Minimal | CUDA | Python 3.12** image.

5. Select the latest version: **2025.2**.

6. For **Deployment size**, select the hardware profile created by your cluster administrator.

   NOTE: For the Knowledge Tuning example, each module subfolder contains an `.env.example` file that defines the environment variables for that module. Alternately, you can define environment variables here in the workbench configuration.

7. Click **Create workbench**.

### Verification

In the **Workbenches** tab for the project, the status of the workbench changes from `Starting` to `Running`.

NOTE: If you made a mistake, you can edit the workbench to make changes.

## Clone the example Git repository

The files for each step in the Knowledge Tuning example end-to-end workflow are organized in subfolders of the `https://github.com/red-hat-data-services/red-hat-ai-examples` Git repository. From your workbench, access the JupyterLab environment and clone the example Git repository.

### Prerequisites

- You created a workbench, as described in *Create a workbench*.

### Procedure

1. From the OpenShift AI dashboard, click the link for your workbench. If prompted, log in and allow JupyterLab to authorize your user.

   Your JupyterLab environment window opens.

   The file-browser window shows the files and folders that are saved inside your own personal space in OpenShift AI.

2. Bring the content of this example inside your JupyterLab environment:

   a. On the toolbar, click the **Git Clone** icon.

   b. Enter the following example Git **https** URL: <https://github.com/red-hat-data-services/red-hat-ai-examples.git>

   c. Select the **Include submodules** option, and then click **Clone**.

   d. In the file browser, double-click the folders to browse to the newly-created **red-hat-ai-examples/examples/knowledge-tuning** folder.

### Verification

In the file browser, view the notebooks that you cloned from Git.

Congratulations! Your workbench is configured and ready for the knowledge training example. The notebooks and supporting README files provide details about each step in the knowledge training workflow.

## Next step

Proceed to [Module 1: Base Model Evaluation](../01_Base_Model_Evaluation/01_Base_Model_Evaluation_README.md).
