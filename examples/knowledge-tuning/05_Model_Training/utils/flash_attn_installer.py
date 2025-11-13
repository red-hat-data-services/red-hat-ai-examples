import json
import platform
import subprocess
import sys
import urllib.request
from pathlib import Path

import torch


def get_latest(
    python_version_short, torch_version_clean, cuda_version, platform_str, cxx11_abi
):
    """
    Helper function to get the latest flash-attention version and build the download URL.

    Args:
        python_version_short: Python version without dots (e.g., "312" for Python 3.12)
        torch_version_clean: PyTorch major.minor version (e.g., "2.8")
        cuda_version: Full CUDA version string (e.g., "12.1.0") or None
        platform_str: Platform string (e.g., "linux_x86_64")
        cxx11_abi: CXX11 ABI setting ("TRUE" or "FALSE")

    Returns:
        str: download_url or None if not compatible
    """
    # Check CUDA availability
    if not cuda_version:
        print("⚠️ CUDA not available, flash-attention requires CUDA")
        return None

    # Get latest flash-attention version from GitHub API
    try:
        api_url = (
            "https://api.github.com/repos/Dao-AILab/flash-attention/releases/latest"
        )
        with urllib.request.urlopen(api_url) as response:
            data = json.loads(response.read())
            flash_attn_version = data["tag_name"].lstrip("v")
    except Exception:
        flash_attn_version = "2.8.3"  # Fallback version

    # Parse CUDA version
    cuda_short = cuda_version.replace(".", "")[:3]
    if len(cuda_short) == 2:
        cuda_short = cuda_short + "0"

    # Print detected configuration
    print("🔍 System Configuration:")
    print(f"  Python: cp{python_version_short}")
    print(f"  PyTorch: v{torch_version_clean}")
    print(f"  CUDA: {cuda_version} (cu{cuda_short})")
    print(f"  Platform: {platform_str}")
    print(f"  CXX11 ABI: {cxx11_abi}")
    print(f"  Flash-Attention: v{flash_attn_version}")

    # Use PyTorch version directly for wheel name
    torch_wheel_version = torch_version_clean

    # Map CUDA version for wheel name (currently only cu12 is available)
    cuda_wheel_version = "cu12"
    if not (cuda_short and cuda_short.startswith("12")):
        print(
            f"⚠️ CUDA {cuda_version} detected, but only CUDA 12 wheels are available, using {cuda_wheel_version}"
        )

    # Construct wheel filename
    wheel_name = f"flash_attn-{flash_attn_version}+{cuda_wheel_version}torch{torch_wheel_version}cxx11abi{cxx11_abi}-cp{python_version_short}-cp{python_version_short}-{platform_str}.whl"

    # Build download URL
    download_url = f"https://github.com/Dao-AILab/flash-attention/releases/download/v{flash_attn_version}/{wheel_name}"

    return download_url


def get_flash_attention_url():
    """
    Detect system configuration and build the appropriate flash-attention wheel URL.
    Returns the download_url or None if not compatible.
    """

    # Detect system configuration
    python_version_short = f"{sys.version_info.major}{sys.version_info.minor}"

    # Get PyTorch and CUDA versions
    torch_version = torch.__version__
    cuda_version = torch.version.cuda if torch.cuda.is_available() else None

    # Parse PyTorch version
    torch_major_minor = ".".join(torch_version.split(".")[:2])
    torch_major_minor_clean = torch_major_minor.split("+")[0]

    # Detect platform
    system = platform.system().lower()
    machine = platform.machine().lower()

    if system == "linux":
        if machine in ["x86_64", "amd64"]:
            platform_str = "linux_x86_64"
        elif machine == "aarch64":
            platform_str = "linux_aarch64"
        else:
            platform_str = f"linux_{machine}"
    elif system == "darwin":
        platform_str = (
            "macosx_" + platform.mac_ver()[0].replace(".", "_") + "_" + machine
        )
    else:
        platform_str = f"{system}_{machine}"

    # Check cxx11 ABI (for Linux with CUDA)
    cxx11_abi = "TRUE"
    if system == "linux" and cuda_version:
        try:
            result = subprocess.run(
                [
                    "python",
                    "-c",
                    "import torch; print(torch._C._GLIBCXX_USE_CXX11_ABI)",
                ],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                cxx11_abi = "TRUE" if result.stdout.strip() == "True" else "FALSE"
        except Exception:
            pass

    # Call the helper function with detected parameters
    return get_latest(
        python_version_short,
        torch_major_minor_clean,
        cuda_version,
        platform_str,
        cxx11_abi,
    )


def download_flash_attention_wheel():
    """
    Download the compatible flash-attention wheel for the current system.
    """
    flash_wheel_url = get_flash_attention_url()
    if flash_wheel_url:
        print("\n" + "=" * 50)
        print("✅ Compatible flash-attn wheel found!")
        print("=" * 50)
        print(f"\nURL: {flash_wheel_url}")

        Download_Path = Path("./python_wheels/")
        Download_Path.mkdir(parents=True, exist_ok=True)
        wheel_file_path = str(Download_Path / flash_wheel_url.split("/")[-1])

        Download_Path = str(Download_Path)

        urllib.request.urlretrieve(flash_wheel_url, wheel_file_path)
        print(f"\nDownloaded flash-attn wheel to: {wheel_file_path}")
        return wheel_file_path
    else:
        print("\n" + "=" * 50)
        print("❌ No compatible flash-attn wheel found")
        print("=" * 50)
        return None
