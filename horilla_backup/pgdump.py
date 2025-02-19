import os
import subprocess


def dump_postgres_db(
    db_name, username, output_file, password=None, host="localhost", port=5432
):
    # Set environment variable for the password if provided
    if password:
        os.environ["PGPASSWORD"] = password

    # Construct the pg_dump command
    dump_command = [
        "pg_dump",
        "-h",
        host,
        "-p",
        str(port),
        "-U",
        username,
        "-F",
        "c",  # Custom format
        "-f",
        output_file,
        db_name,
    ]

    try:
        # Execute the pg_dump command
        result = subprocess.run(
            dump_command, check=True, text=True, capture_output=True
        )
    except subprocess.CalledProcessError as e:
        pass
    finally:
        # Clean up the environment variable
        if password:
            del os.environ["PGPASSWORD"]
