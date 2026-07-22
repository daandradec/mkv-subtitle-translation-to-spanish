#!/usr/bin/env bash

set -euo pipefail

source "$(dirname -- "${BASH_SOURCE[0]}")/lib/VideoToolkit.Infrastructure.sh"

setup_python_environment() {
  local skip_install="$1"
  local ensure_cuda="$2"
  local requested_python="$3"
  initialize_video_generated_environment system
  mkdir -p "$VIDEO_PROJECT_ROOT/inputs" "$VIDEO_PROJECT_ROOT/outputs"
  local python_command venv_python
  python_command="$(resolve_python_command "$requested_python")"
  ensure_ubuntu_venv "$python_command"
  venv_python="$VIDEO_PROJECT_ROOT/.venv/bin/python"

  if [[ "$skip_install" == "false" ]]; then
    "$venv_python" -m pip install --upgrade pip setuptools wheel
    install_requirements_if_changed "$venv_python" "$VIDEO_PROJECT_ROOT/requirements.txt" "$VIDEO_TOOLKIT_CACHE_ROOT/install-state/requirements.sha256"
    install_requirements_if_changed "$venv_python" "$VIDEO_PROJECT_ROOT/requirements-whisperx.txt" "$VIDEO_TOOLKIT_CACHE_ROOT/install-state/requirements-whisperx.sha256" true
  fi

  if [[ "$skip_install" == "false" && "$ensure_cuda" == "true" ]]; then
    if ! "$venv_python" -c 'import torch, sys; sys.exit(0 if torch.cuda.is_available() else 1)' >/dev/null 2>&1; then
      "$venv_python" -m pip install --upgrade --force-reinstall \
        torch==2.8.0 torchvision==0.23.0 torchaudio==2.8.0 \
        --index-url https://download.pytorch.org/whl/cu128
    fi
    "$venv_python" -c 'import torch, sys; sys.exit(0 if torch.cuda.is_available() else 1)'
  fi

  local external_tool
  for external_tool in ffmpeg ffprobe mkvmerge; do
    if ! command -v "$external_tool" >/dev/null 2>&1; then
      printf 'Warning: required external tool is not on PATH: %s\n' "$external_tool" >&2
    fi
  done
  remove_video_temporary_child system
  remove_video_temporary_child logs
  assert_no_generated_artifacts_at_root
  printf 'Python environment: %s\n' "$venv_python"
}

build_python_package() {
  initialize_video_generated_environment system
  local venv_python="$VIDEO_PROJECT_ROOT/.venv/bin/python"
  if [[ ! -x "$venv_python" ]]; then
    local python_command
    python_command="$(resolve_python_command "${PYTHON_COMMAND:-python3.12}")"
    ensure_ubuntu_venv "$python_command"
  fi
  mkdir -p "$VIDEO_TOOLKIT_CACHE_ROOT/packages/python"
  local build_succeeded=false
  if (
    cd "$VIDEO_PROJECT_ROOT"
    "$venv_python" -m pip install --upgrade 'build>=1.2' 'setuptools>=68' wheel
    "$venv_python" -m build --wheel --outdir "$VIDEO_TOOLKIT_CACHE_ROOT/packages/python"
    assert_no_generated_artifacts_at_root
  ); then
    build_succeeded=true
  fi
  if [[ "$build_succeeded" == "true" ]]; then
    remove_video_temporary_child build
    remove_video_temporary_child video_toolkit_workflows.egg-info
    remove_video_temporary_child system
    remove_video_temporary_child logs
    printf 'Cached Python package: %s\n' "$VIDEO_TOOLKIT_CACHE_ROOT/packages/python"
  else
    return 1
  fi
}

run_test_suite() {
  initialize_video_generated_environment tests
  local venv_python="$VIDEO_PROJECT_ROOT/.venv/bin/python"
  if [[ ! -x "$venv_python" ]]; then
    printf 'Virtual environment not found. Run setup-python-environment first.\n' >&2
    return 1
  fi
  export PYTHONDONTWRITEBYTECODE=1
  if (cd "$VIDEO_PROJECT_ROOT" && "$venv_python" "$VIDEO_PROJECT_ROOT/tests/run_all.py"); then
    assert_no_generated_artifacts_at_root
    remove_video_temporary_child tests
  else
    return 1
  fi
}

clean_temporary_files() {
  initialize_video_generated_environment system
  local children=(build video_toolkit_workflows.egg-info runtime tests system logs)
  local child
  for child in "${children[@]}"; do
    remove_video_temporary_child "$child"
  done

  assert_no_generated_artifacts_at_root
  printf 'Temporary cleanup completed under: %s\n' "$VIDEO_TOOLKIT_TMP_ROOT"
}

clean_cache_files() {
  initialize_video_generated_environment system
  local child
  for child in pip python models runtime install-state packages; do
    remove_video_cache_child "$child"
  done

  while IFS= read -r -d '' cache_path; do
    if [[ -L "$cache_path" ]]; then
      printf 'Refusing to remove Python cache symlink: %s\n' "$cache_path" >&2
      return 1
    fi
    rm -rf -- "$cache_path"
  done < <(find \
    "$VIDEO_PROJECT_ROOT/.agents" \
    "$VIDEO_PROJECT_ROOT/scripts" \
    "$VIDEO_PROJECT_ROOT/src" \
    "$VIDEO_PROJECT_ROOT/tests" \
    -type d -name __pycache__ -print0 2>/dev/null)
  remove_video_temporary_child system
  assert_no_generated_artifacts_at_root
  printf 'Cache cleanup completed under: %s\n' "$VIDEO_TOOLKIT_CACHE_ROOT"
}

verify_repository() {
  initialize_video_generated_environment system
  local required missing=()
  for required in \
    .agents .cache .tmp .venv inputs outputs scripts src tests \
    pyproject.toml setup.cfg requirements.txt requirements-whisperx.txt \
    scripts/manage_video_toolkit.ps1 scripts/manage_video_toolkit.sh \
    scripts/lib/VideoToolkit.Infrastructure.psm1 \
    scripts/lib/VideoToolkit.Infrastructure.sh; do
    [[ -e "$VIDEO_PROJECT_ROOT/$required" ]] || missing+=("$required")
  done
  remove_video_temporary_child system
  if [[ ${#missing[@]} -gt 0 ]]; then
    printf 'Repository verification failed; missing: %s\n' "${missing[*]}" >&2
    return 1
  fi
  local legacy
  for legacy in input output; do
    if [[ -e "$VIDEO_PROJECT_ROOT/$legacy" ]]; then
      printf 'Repository verification failed; legacy working directory is not allowed: %s\n' "$legacy" >&2
      return 1
    fi
  done
  assert_no_generated_artifacts_at_root
  printf 'Repository structure verified: %s\n' "$VIDEO_PROJECT_ROOT"
}

show_help() {
  cat <<'EOF'
Video toolkit repository manager

Commands:
  setup-python-environment [--skip-install] [--ensure-cuda-torch] [--python PATH]
  build-python-package
  run-test-suite
  clean-temporary-files
  clean-cache-files
  verify-repository
  help
EOF
}

command_name="${1:-help}"
[[ $# -gt 0 ]] && shift
skip_install=false
ensure_cuda=false
python_command="${PYTHON_COMMAND:-python3.12}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-install) skip_install=true ;;
    --ensure-cuda-torch) ensure_cuda=true ;;
    --python)
      shift
      python_command="${1:?--python requires an executable}"
      ;;
    -h|--help) command_name=help ;;
    *) printf 'Unknown argument: %s\n' "$1" >&2; exit 2 ;;
  esac
  shift
done

VIDEO_PROJECT_ROOT="$(video_project_root)"
case "$command_name" in
  setup-python-environment) setup_python_environment "$skip_install" "$ensure_cuda" "$python_command" ;;
  build-python-package) build_python_package ;;
  run-test-suite) run_test_suite ;;
  clean-temporary-files) clean_temporary_files ;;
  clean-cache-files) clean_cache_files ;;
  verify-repository) verify_repository ;;
  help|-h|--help) show_help ;;
  *) printf 'Unknown command: %s\n' "$command_name" >&2; show_help >&2; exit 2 ;;
esac
