import os
import re
import shutil
from pathlib import Path
import sys

REPO_ROOT = "."
CDK_ROOT = f"{REPO_ROOT}/airbyte-cdk/java/airbyte-cdk"
EXCLUDE_DIRS = [
    "target", "out", "build", "dist",
    "node_modules", "lib", "bin", "__pycache__", ".gradle"
]
EXCLUDE_FILES = [
    "pom.xml", "README.md", "LICENSE", "build", ".coverage.*", "_temp_*",
]
def move_files(source_dir, dest_dir, path_desc):
    if os.path.isdir(source_dir):
        print(f"Moving '{path_desc}' files (ignoring existing)...\n - From: {source_dir}\n - To:   {dest_dir}")
        os.makedirs(dest_dir, exist_ok=True)
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                src_file = os.path.join(root, file)
                dst_file = os.path.join(dest_dir, file)

                os.makedirs(os.path.dirname(dst_file), exist_ok=True)

                shutil.move(src_file, dst_file)
    else:
        print(f"The source directory does not exist: {source_dir} ('{path_desc}')")

def remove_empty_dirs(root_dir):
    for root, dirs, files in os.walk(root_dir, topdown=False):
        for dir in dirs:
            path = os.path.join(root, dir)
            if not os.listdir(path):
                os.rmdir(path)

def list_remnant_files(from_dir: str):
    # List remnant files in the OLD_PACKAGE_ROOT
    print(f"Files remaining in {from_dir}:")
    for root, dirs, files in os.walk(from_dir):
        for f in files:
            print(os.path.join(root, f))

def move_package(old_package_root):
    # Define source and destination directories
    old_main_path = os.path.join(old_package_root, "src/main/java/io/airbyte")
    old_test_path = os.path.join(old_package_root, "src/test/java/io/airbyte")
    old_integtest_path = os.path.join(old_package_root, "src/test-integration/java/io/airbyte")
    old_testfixture_path = os.path.join(old_package_root, "src/testfixtures/java/io/airbyte")
    old_main_resources_path = os.path.join(old_package_root, "src/main/resources")
    old_test_resources_path = os.path.join(old_package_root, "src/test/resources")
    old_integtest_resources_path = os.path.join(old_package_root, "src/test-integration/resources")

    dest_main_path = os.path.join(CDK_ROOT, "src/main/java/io/airbyte/cdk")
    dest_test_path = os.path.join(CDK_ROOT, "src/test/java/io/airbyte/cdk")
    dest_integtest_path = os.path.join(CDK_ROOT, "src/test-integration/java/io/airbyte/cdk")
    dest_testfixture_path = os.path.join(CDK_ROOT, "src/testFixtures/java/io/airbyte/cdk")

    old_project_name = str(Path(old_package_root).parts[-1])
    dest_main_resources_path = os.path.join(CDK_ROOT, "src/main/resources", old_project_name)
    dest_test_resources_path = os.path.join(CDK_ROOT, "src/test/resources", old_project_name)
    dest_integtest_resources_path = os.path.join(CDK_ROOT, "src/test-integration/resources", old_project_name)
    remnants_archive_path = os.path.join(CDK_ROOT, "archive", old_project_name)

    # Define source and destination directories as lists

    paths = [
        ("main classes", old_main_path, dest_main_path),
        ("main test classes", old_test_path, dest_test_path),
        ("integ test classes", old_integtest_path, dest_integtest_path),
        ("test fixtures", old_testfixture_path, dest_testfixture_path),
        ("main resources", old_main_resources_path, dest_main_resources_path),
        ("test resources", old_test_resources_path, dest_test_resources_path),
        ("integ test resources", old_integtest_resources_path, dest_integtest_resources_path),
        ("remnants to archive", old_package_root, remnants_archive_path)
    ]

    remove_empty_dirs(old_package_root)
    for path_desc, source_dir, dest_dir in paths:
        move_files(source_dir, dest_dir, path_desc)
    remove_empty_dirs(old_package_root)


def migrate_package_refs(
    text_pattern: str,
    text_replacement: str,
    within_dir: str,
    exclude_files: list,
    exclude_dirs: list,
):
    """
    Migrates a Java package to the new CDK package structure.

    Args:
        package_root (str): The root directory of the package to migrate.
        exclude_files (list): A list of file patterns to exclude from the migration.
        exclude_dirs (list): A list of directory patterns to exclude from the migration.

    Returns:
        None
    """
    # Define the files to exclude from the search
    exclude_files_pattern = "|".join(exclude_files)
    exclude_files_regex = re.compile(exclude_files_pattern)

    # Walk the directory tree and perform the find and replace operation on each file
    for root, dirs, files in os.walk(within_dir):
        # Exclude files that match the exclude_files pattern
        files = [f for f in files if not exclude_files_regex.match(f)]

        for file in files:
            file_path = os.path.join(root, file)
            if (
                any(
                    [
                        exclude_dir in file_path.split("/")
                        for exclude_dir in exclude_dirs
                    ]
                )
            ):
                continue

            # print("Scanning file: ", file_path)
            # Exclude files that match the exclude_files pattern
            if exclude_files_regex.match(file):
                continue

            # Read the file contents
            with open(file_path, "r") as f:
                contents = f.read()

            # Perform the find and replace operation
            new_contents = re.sub(text_pattern, text_replacement, contents)

            # Write the updated contents back to the file
            with open(file_path, "w") as f:
                f.write(new_contents)
        else:
            print(f"No files found to scan within {within_dir}")

def update_cdk_package_defs() -> None:
    """Within CDK_ROOT, packages should be declared as 'package io.airbyte.cdk...'"""
    migrate_package_refs(
        text_pattern=r"package io\.airbyte\.(?!cdk\.)(?!cdk$)",
        text_replacement=r"package io.airbyte.cdk.",
        within_dir=CDK_ROOT,
        exclude_files=EXCLUDE_FILES,
        exclude_dirs=EXCLUDE_DIRS,
    )


def migrate_all_packages_refs() -> None:
    for text_pattern, text_replacement, within_dir, exclude_dirs in [
        (
            r"(?<!package )io\.airbyte\.(db|integrations\.base|integrations\.debezium|integrations\.destination\.NamingConventionTransformer|integrations\.destination\.StandardNameTransformer|integrations\.destination\.jdbc|integrations\.destination\.record_buffer|integrations\.destination\.normalization|integrations\.destination\.buffered_stream_consumer|integrations\.destination\.dest_state_lifecycle_manager|integrations\.destination\.staging|integrations\.destination_async|integrations\.source\.jdbc|integrations\.source\.relationaldb|integrations\.util|integrations\.BaseConnector|test\.utils)",
            r"io.airbyte.cdk.\2",
            REPO_ROOT,
            ["target", "out", "build", "dist", "node_modules", "lib", "bin"]
        )
    ]:
        migrate_package_refs(
            text_pattern,
            text_replacement,
            within_dir=within_dir,
            exclude_files=EXCLUDE_FILES,
            exclude_dirs=list(set(exclude_dirs + EXCLUDE_DIRS)),
        )


def main() -> None:
    # Remove empty directories in CDK_ROOT
    remove_empty_dirs(CDK_ROOT)

    # Check if there was a CLI argument passed
    paths_to_migrate: list[str] = [
        "airbyte-integrations/bases/base-java",
    ]
    if len(sys.argv) > 1:
        paths_to_migrate = [sys.argv[1]]

    for old_package_root in paths_to_migrate:
        # Remove empty directories in the OLD_PACKAGE_ROOT
        move_package(old_package_root)
        remove_empty_dirs(old_package_root)
        update_cdk_package_defs()

    # Move remaining files in the OLD_PACKAGE_ROOT to the CDK 'archive' directory
    # print(f"Moving renaming files...\n - From: {OLD_PACKAGE_ROOT}\n - To:   {REMNANTS_ARCHIVE_PATH}")
    # os.makedirs(REMNANTS_ARCHIVE_PATH, exist_ok=True)
    # shutil.move(OLD_PACKAGE_ROOT, REMNANTS_ARCHIVE_PATH)

    print("Migration operation complete!")


if __name__ == "__main__":
    main()

