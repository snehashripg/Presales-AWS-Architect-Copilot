#!/usr/bin/env python3
"""
Package RFx Agents as Lambda Layer (auto-detects Python version)
Run in SageMaker: python 01_package_lambda_layer.py
"""

import os
import shutil
import subprocess
import zipfile
import sys
from datetime import datetime
from pathlib import Path


def create_lambda_layer_package():
    """Package agents and dependencies for Lambda Layer"""

    print("=" * 70)
    print("📦 PACKAGING LAMBDA LAYER")
    print("=" * 70)

    # Detect current Python version
    py_major = sys.version_info.major
    py_minor = sys.version_info.minor
    python_version_str = f"{py_major}.{py_minor}"
    print(f"\n🐍 Detected Python version: {python_version_str}")

    # Define paths
    backend_dir = Path.cwd()
    package_dir = backend_dir / "lambda_package"
    python_dir = package_dir / "python"

    # Clean previous package
    if package_dir.exists():
        print(f"\n🗑️  Removing old package directory...")
        shutil.rmtree(package_dir)

    # Create directory structure
    print(f"\n📁 Creating package structure...")
    python_dir.mkdir(parents=True, exist_ok=True)
    print(f"   Created: {python_dir}")

    # Install dependencies
    print(f"\n📥 Installing dependencies to package (for Python {python_version_str})...")

    deps = [
        "boto3>=1.28.0",
        "botocore>=1.31.0",
        "python-docx>=0.8.11",
        "PyMuPDF==1.23.26",
        "jsonschema>=4.0.0",
        "strands-agents",
        "pydantic>=2.6.0,<3",
        "pydantic-core>=2.16.0,<3"
    ]

    for dep in deps:
        print(f"   Installing: {dep}")
        try:
            subprocess.run(
                [
                    "pip",
                    "install",
                    dep,
                    "-t",
                    str(python_dir),
                    "--platform",
                    "manylinux2014_x86_64",
                    "--only-binary",
                    ":all:",
                    "--implementation",
                    "cp",
                    "--python-version",
                    python_version_str,
                    "--quiet",
                ],
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError as e:
            print(f"   ⚠️  Warning: {dep} installation had issues")
            print(e.stderr.decode()[:300])

    print(f"   ✅ Dependencies installed successfully")

    # Copy agent files
    print(f"\n📄 Copying agent files...")
    agent_files = [
        "rfx_orchestrator_agent.py",
        "rfx_parsing_agent.py",
        "clarification_agent.py",
        "pricing_funding_agent.py",
        "sow_drafting_agent.py",
        "agentcore_wrapper.py",
    ]

    for agent_file in agent_files:
        src = backend_dir / agent_file
        dst = python_dir / agent_file
        if src.exists():
            shutil.copy2(src, dst)
            print(f"   ✅ Copied: {agent_file}")
        else:
            print(f"   ⚠️  Not found: {agent_file}")

    # Create versioned ZIP name
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = f"agents-layer-py{python_version_str.replace('.', '')}-{timestamp}.zip"
    zip_path = package_dir / zip_filename

    print(f"\n📦 Creating ZIP archive: {zip_filename}")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(python_dir):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(package_dir)
                zipf.write(file_path, arcname)

    zip_size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"   ✅ Created: {zip_path}")
    print(f"   📊 Size: {zip_size_mb:.2f} MB")

    if zip_size_mb > 50:
        print(f"   ⚠️  WARNING: Layer size exceeds 50MB Lambda limit!")

    # Summary
    print("\n" + "=" * 70)
    print("✅ PACKAGING COMPLETE")
    print("=" * 70)
    print(f"\n📦 Package location: {zip_path}")
    print(f"📊 Package size: {zip_size_mb:.2f} MB")
    print(f"💡 Next: Run 02_upload_and_create_layer.py to upload and publish.")
    
    return str(zip_path)


if __name__ == "__main__":
    try:
        zip_path = create_lambda_layer_package()
        print(f"\n✅ SUCCESS! Package ready: {zip_path}")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
