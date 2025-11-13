# Setup

## Navigation

- Overview - [Knowledge Tuning Overview](../README.md)
- Step 00 - Setup
- Step 01 - [Base Model Evaluation](../01_Base_Model_Evaluation/01_Base_Model_Evaluation_README.md)
- Step 02 - [Data Processing](../02_Data_Processing/02_Data_Processing_README.md)
- Step 03 - [Knowledge Generation](../03_Knowledge_Generation/03_Knowledge_Generation_README.md)
- Step 04 - [Knowledge Mixing](../04_Knowledge_Mixing/04_Knowledge_Mixing_README.md)
- Step 05 - [Model Training](../05_Model_Training/05_Model_Training_README.md)
- Step 06 - [Evaluation](../06_Evaluation/06_Evaluation_README.md)

## Set up your working environment

To use the Knowledge Tuning example, follow these steps to set up your working environment on your Red Hat OpenShift AI cluster:

1. [Configure resources on the OpenShift cluster](#configure-resources-on-the-openshift-cluster)
2. [Create a project](#create-a-project)
3. [Create a workbench](#create-a-workbench)
4. [Clone the example Git repository](#clone-the-example-git-repository)

## Configure resources on the OpenShift cluster

Ask your OpenShift cluster administrator to configure your cluster as follows:

- **GPUs:** GPUs are optional for the preprocessing and mixing notebooks. In the model training step, fine-tuning
large models requires at least one NVIDIA A100/40GB or similar. Training smaller student models requires 8–16 GB GPU.

- **Persistent Volumes:** Attach a persistent volume with at least 200 GB.

## Create a project

To implement an AI workflow in OpenShift AI, you must create a project. Projects help your team to organize and work
together on resources within separated namespaces. From a project you can create many workbenches, each with their own
IDE environment (for example, JupyterLab), and each with their own connections and cluster storage.

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

A workbench is an instance of your development and experimentation environment. When you create a workbench, you select
a workbench image that has the tools and libraries that you need for developing models.

### Prerequisites

- You created a project.

### Procedure

1. Navigate to the project detail page for the project that you created in *Create a project*.

2. Click the **Workbenches** tab, and then click **Create workbench**.

3. Fill out the name and description.

   Red Hat OpenShift AI provides several supported workbench images. In the **Workbench image** section, you can select
   one of the default images or a custom image that an administrator has set up for you. The **Jupyter | Minimal | CUDA | Python 3.12**
   has the libraries needed for this example.

4. Select the latest **Jupyter | Minimal | CUDA | Python 3.12** image.

5. Select the latest version: **2025.2**.

6. For **Deployment size**, select the appropriate size for your workload.

   <!-- need to complete these steps for storage and environment variables.
   It looks like - for environment variables - they need to set these at the notebook level rather than here in the workbench - TBD
   -->

7. Click **Create workbench**.

### Verification

In the **Workbenches** tab for the project, the status of the workbench changes from `Starting` to `Running`.

NOTE: If you made a mistake, you can edit the workbench to make changes.

## Clone the example Git repository

The JupyterLab environment is a web-based environment, but everything you do inside it happens on Red Hat OpenShift AI
and is powered by the OpenShift cluster. This means that, without having to install and maintain anything on your own
computer, and without using valuable local resources such as CPU, GPU and RAM, you can conduct your work in this powerful
and stable managed environment.

### Prerequisites

You created a workbench, as described in *Create a workbench*.

### Procedure

1. Click the link for your workbench. If prompted, log in and allow JupyterLab to authorize your user.

   Your JupyterLab environment window opens.

   The file-browser window shows the files and folders that are saved inside your own personal space in OpenShift AI.

2. Bring the content of this example inside your JupyterLab environment:

   a. On the toolbar, click the **Git Clone** icon.

   b. Enter the following example Git **https** URL: <https://github.com/red-hat-data-services/red-hat-ai-examples.git>

   c. Select the **Include submodules** option, and then click **Clone**.

   d. In the file browser, double-click the folders to browse to the newly-created **red-hat-ai-examples/examples/knowledge-tuning** folder.

### Verification

In the file browser, view the notebooks that you cloned from Git.

Congratulations! Your workbench is configured and ready for the knowledge training example. The notebooks and supporting
README files provide details about each step in the knowledge training workflow.

## Next step

Proceed to [Step 1: Base Model Evaluation](../01_Base_Model_Evaluation/01_Base_Model_Evaluation_README.md).
