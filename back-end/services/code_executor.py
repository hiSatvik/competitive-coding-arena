import io
import os
import tarfile
import docker

EXECUTOR_IMAGE = os.getenv("EXECUTOR_IMAGE", "gcc:13-bookworm")

def _put_file_in_container(container, path: str, filename: str, content: str):
    tar_stream = io.BytesIO()
    encoded_content = content.encode("utf-8")
    with tarfile.open(fileobj=tar_stream, mode="w") as tar:
        tarinfo = tarfile.TarInfo(name=filename)
        tarinfo.size = len(encoded_content)
        tar.addfile(tarinfo, io.BytesIO(encoded_content))
    tar_stream.seek(0)
    container.put_archive(path=path, data=tar_stream)

def execute_cpp_code(code: str, test_cases: list[dict]) -> dict:
    client = docker.from_env()
    container = None

    try:
        container = client.containers.run(
            image=EXECUTOR_IMAGE,
            command="sleep 30",
            detach=True,
            network_disabled=True,
            mem_limit="128m",
            nano_cpus=int(0.5 * 1e9),
            working_dir="/app",
        )

        _put_file_in_container(container, "/app", "main.cpp", code)

        compile_result = container.exec_run("g++ -O2 main.cpp -o main")
        if compile_result.exit_code != 0:
            return {
                "status": "Compilation Error",
                "error": compile_result.output.decode("utf-8"),
            }

        results = []
        all_passed = True

        for idx, tc in enumerate(test_cases):
            tc_input = tc.get("input", "")
            expected_output = tc.get("expected_output", "").strip()

            _put_file_in_container(container, "/app", "input.txt", tc_input)

            run_result = container.exec_run("sh -c 'timeout 2s ./main < input.txt'")

            if run_result.exit_code == 124:
                results.append({"test_case": idx + 1, "status": "Time Limit Exceeded"})
                all_passed = False
                continue
            if run_result.exit_code != 0:
                results.append(
                    {
                        "test_case": idx + 1,
                        "status": f"Runtime Error (Code {run_result.exit_code})",
                    }
                )
                all_passed = False
                continue

            actual_output = run_result.output.decode("utf-8").strip()

            if actual_output == expected_output:
                results.append({"test_case": idx + 1, "status": "Passed"})
            else:
                results.append(
                    {
                        "test_case": idx + 1,
                        "status": "Failed",
                        "expected": expected_output,
                        "actual": actual_output,
                    }
                )
                all_passed = False

        return {
            "status": "Accepted" if all_passed else "Rejected",
            "results": results,
        }

    except Exception as e:
        return {"status": "System Error", "error": str(e)}

    finally:
        if container:
            try:
                container.kill()
                container.remove()
            except Exception:
                pass
