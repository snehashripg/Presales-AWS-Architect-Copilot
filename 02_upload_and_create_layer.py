#!/usr/bin/env python3
"""
Upload Lambda Layer to S3 and recreate it (auto-detects latest ZIP file)
Run in SageMaker: python 02_upload_and_create_layer.py
"""

import boto3
import json
from pathlib import Path
from datetime import datetime
from botocore.exceptions import ClientError


def get_latest_zip_file(directory: Path):
    """Return the most recent ZIP file in the given directory."""
    zip_files = list(directory.glob("*.zip"))
    if not zip_files:
        return None
    return max(zip_files, key=lambda f: f.stat().st_mtime)


def upload_and_create_layer():
    """Recreate Lambda Layer: delete old versions, upload ZIP, create new version"""

    print("=" * 70)
    print("☁️  UPLOAD AND RECREATE LAMBDA LAYER")
    print("=" * 70)

    # Configuration
    region = "us-east-1"
    s3_bucket = "presales-rfp-outputs"
    layer_name = "rfx-agents-layer"
    package_dir = Path.cwd() / "lambda_package"

    # Auto-detect latest ZIP file
    zip_path = get_latest_zip_file(package_dir)
    if not zip_path or not zip_path.exists():
        print(f"\n❌ ERROR: No ZIP files found in {package_dir}")
        print("💡 Run 01_package_lambda_layer.py first!")
        return None

    print(f"\n📦 Using latest ZIP package: {zip_path.name}")
    zip_size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"📊 Size: {zip_size_mb:.2f} MB")

    # Clients
    s3 = boto3.client("s3", region_name=region)
    lambda_client = boto3.client("lambda", region_name=region)

    # STEP 1 — Delete existing layer versions
    print("\n🧹 STEP 1: Deleting existing layer versions (if any)...")
    try:
        versions = lambda_client.list_layer_versions(LayerName=layer_name).get("LayerVersions", [])
        if versions:
            for v in versions:
                version_number = v["Version"]
                arn = v["LayerVersionArn"]
                print(f"   🗑️  Deleting version {version_number} ({arn}) ...")
                try:
                    lambda_client.delete_layer_version(LayerName=layer_name, VersionNumber=version_number)
                except ClientError as ce:
                    print(f"   ⚠️  Could not delete version {version_number}: {ce}")
        else:
            print("   ℹ️  No existing layer versions found.")
    except ClientError as e:
        if "ResourceNotFoundException" in str(e):
            print("   ℹ️  Layer does not exist yet.")
        else:
            print(f"   ⚠️  Error checking layers: {e}")

    # STEP 2 — Upload ZIP to S3
    print(f"\n☁️  STEP 2: Uploading ZIP to S3 bucket `{s3_bucket}` ...")
    s3_key = f"lambda_layers/{zip_path.name}"
    try:
        print(f"   Uploading to: s3://{s3_bucket}/{s3_key}")
        with open(zip_path, "rb") as f:
            s3.put_object(Bucket=s3_bucket, Key=s3_key, Body=f)
        print("   ✅ Upload successful.")
    except Exception as e:
        print(f"   ❌ Upload failed: {e}")
        return None

    # STEP 3 — Publish new layer version
    print(f"\n⚡ STEP 3: Publishing new Lambda layer `{layer_name}` ...")
    try:
        response = lambda_client.publish_layer_version(
            LayerName=layer_name,
            Description=f"RFx Agents Layer - created on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            Content={"S3Bucket": s3_bucket, "S3Key": s3_key},
            CompatibleRuntimes=["python3.11"],
            CompatibleArchitectures=["x86_64"],
        )
        layer_arn = response["LayerVersionArn"]
        layer_version = response["Version"]
        print(f"   ✅ New Layer Version Created!")
        print(f"   📝 ARN: {layer_arn}")
        print(f"   🔢 Version: {layer_version}")
    except Exception as e:
        print(f"   ❌ Layer creation failed: {e}")
        import traceback
        traceback.print_exc()
        return None

    # STEP 4 — Save layer info locally
    layer_info = {
        "layer_name": layer_name,
        "layer_arn": layer_arn,
        "version": layer_version,
        "s3_bucket": s3_bucket,
        "s3_key": s3_key,
        "created_at": datetime.now().isoformat(),
        "package_file": zip_path.name
    }

    info_file = Path.cwd() / "lambda_layer_info.json"
    with open(info_file, "w") as f:
        json.dump(layer_info, f, indent=2)
    print(f"\n💾 Layer info saved to: {info_file}")

    print("\n" + "=" * 70)
    print("✅ LAYER RECREATION COMPLETE")
    print("=" * 70)
    print(f"\n📝 Layer ARN: {layer_arn}")
    print(f"🔢 Version: {layer_version}")
    print(f"📦 Source ZIP: {zip_path.name}")
    print(f"\n💡 Next: Attach this new layer ARN to your Lambda function.")

    return layer_info


if __name__ == "__main__":
    try:
        info = upload_and_create_layer()
        if info:
            print(f"\n✅ SUCCESS! Layer ARN: {info['layer_arn']}")
        else:
            print("\n❌ FAILED to recreate layer.")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
