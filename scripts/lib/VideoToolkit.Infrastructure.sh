#!/usr/bin/env bash

# Shared Bash infrastructure for the repository manager. This file is sourced;
# user-facing commands remain in scripts/manage_video_toolkit.sh.

video_project_root() {
  cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." >/dev/null 2>&1
  pwd -P
}

initialize_video_generated_environment() {
  local area="${1:-system}"
  VIDEO_PROJECT_ROOT="${VIDEO_PROJECT_ROOT:-$(video_project_root)}"
  VIDEO_TOOLKIT_TMP_ROOT="$VIDEO_PROJECT_ROOT/.tmp"
  VIDEO_TOOLKIT_CACHE_ROOT="$VIDEO_PROJECT_ROOT/.cache"
  local generated_root
  for generated_root in "$VIDEO_TOOLKIT_TMP_ROOT" "$VIDEO_TOOLKIT_CACHE_ROOT"; do
    if [[ -L "$generated_root" ]]; then
      printf 'A repository-generated root cannot be a symlink: %s\n' "$generated_root" >&2
      return 1
    fi
  done

  mkdir -p \
    "$VIDEO_TOOLKIT_CACHE_ROOT/pip" \
    "$VIDEO_TOOLKIT_CACHE_ROOT/python" \
    "$VIDEO_TOOLKIT_CACHE_ROOT/models/huggingface" \
    "$VIDEO_TOOLKIT_CACHE_ROOT/models/torch" \
    "$VIDEO_TOOLKIT_CACHE_ROOT/models/whisper" \
    "$VIDEO_TOOLKIT_CACHE_ROOT/runtime" \
    "$VIDEO_TOOLKIT_CACHE_ROOT/install-state" \
    "$VIDEO_TOOLKIT_CACHE_ROOT/packages/python"

  local process_tmp="$VIDEO_TOOLKIT_TMP_ROOT/system"
  if [[ "$area" == "tests" ]]; then
    process_tmp="$VIDEO_TOOLKIT_TMP_ROOT/tests"
  elif [[ "$area" == "runtime" ]]; then
    process_tmp="$VIDEO_TOOLKIT_TMP_ROOT/runtime"
  fi
  mkdir -p "$process_tmp"

  export VIDEO_PROJECT_ROOT VIDEO_TOOLKIT_TMP_ROOT VIDEO_TOOLKIT_CACHE_ROOT
  export VIDEO_TOOLKIT_TEMP_CATEGORY="$area"
  export TEMP="$process_tmp" TMP="$process_tmp" TMPDIR="$process_tmp"
  export PIP_CACHE_DIR="$VIDEO_TOOLKIT_CACHE_ROOT/pip"
  export PYTHONPYCACHEPREFIX="$VIDEO_TOOLKIT_CACHE_ROOT/python"
  export HF_HOME="$VIDEO_TOOLKIT_CACHE_ROOT/models/huggingface"
  export HUGGINGFACE_HUB_CACHE="$HF_HOME/hub"
  export TORCH_HOME="$VIDEO_TOOLKIT_CACHE_ROOT/models/torch"
  export WHISPER_CACHE_DIR="$VIDEO_TOOLKIT_CACHE_ROOT/models/whisper"
  export XDG_CACHE_HOME="$VIDEO_TOOLKIT_CACHE_ROOT/runtime"
}

assert_no_generated_artifacts_at_root() {
  local forbidden
  for forbidden in build video_toolkit_workflows.egg-info; do
    if [[ -e "$VIDEO_PROJECT_ROOT/$forbidden" ]]; then
      printf 'Temporary packaging artifact escaped .tmp: %s\n' "$VIDEO_PROJECT_ROOT/$forbidden" >&2
      return 1
    fi
  done
}

remove_video_temporary_child() {
  local child_name="$1"
  if [[ ! "$child_name" =~ ^[A-Za-z0-9._-]+$ ]]; then
    printf 'Unsafe temporary child name: %s\n' "$child_name" >&2
    return 1
  fi
  local target="$VIDEO_TOOLKIT_TMP_ROOT/$child_name"
  if [[ -L "$target" ]]; then
    printf 'Refusing to remove temporary symlink: %s\n' "$target" >&2
    return 1
  fi
  if [[ -d "$target" ]]; then
    rm -rf -- "$target"
  fi
}

remove_video_cache_child() {
  local child_name="$1"
  if [[ ! "$child_name" =~ ^[A-Za-z0-9._-]+$ ]]; then
    printf 'Unsafe cache child name: %s\n' "$child_name" >&2
    return 1
  fi
  local target="$VIDEO_TOOLKIT_CACHE_ROOT/$child_name"
  if [[ -L "$target" ]]; then
    printf 'Refusing to remove cache symlink: %s\n' "$target" >&2
    return 1
  fi
  if [[ -d "$target" ]]; then
    rm -rf -- "$target"
  fi
}

resolve_python_command() {
  local requested="$1"
  if command -v "$requested" >/dev/null 2>&1; then
    printf '%s\n' "$requested"
    return 0
  fi
  if command -v python3 >/dev/null 2>&1 && [[ "$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')" == "3.12" ]]; then
    printf 'python3\n'
    return 0
  fi
  printf 'Python 3.12 is required. Install python3.12 and python3.12-venv.\n' >&2
  return 1
}

ensure_ubuntu_venv() {
  local python_command="$1"
  local venv_dir="$VIDEO_PROJECT_ROOT/.venv"
  local venv_python="$venv_dir/bin/python"
  if [[ -d "$venv_dir" && ! -x "$venv_python" ]] && find "$venv_dir" -mindepth 1 -maxdepth 1 -print -quit | grep -q .; then
    printf 'The existing .venv is not an Ubuntu virtual environment: %s\n' "$venv_dir" >&2
    printf 'Do not share the same .venv between Windows and Ubuntu.\n' >&2
    return 1
  fi
  if [[ ! -x "$venv_python" ]]; then
    "$python_command" -m venv "$venv_dir"
  fi
  if [[ "$($venv_python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')" != "3.12" ]]; then
    printf 'The existing virtual environment does not use Python 3.12: %s\n' "$venv_dir" >&2
    return 1
  fi
}

hash_file() {
  local venv_python="$1"
  local path="$2"
  "$venv_python" -c 'import hashlib, pathlib, sys; print(hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest().upper())' "$path"
}

install_requirements_if_changed() {
  local venv_python="$1"
  local requirements_path="$2"
  local marker_path="$3"
  local optional="${4:-false}"
  [[ -f "$requirements_path" ]] || return 0
  local current_hash previous_hash=""
  current_hash="$(hash_file "$venv_python" "$requirements_path")"
  [[ -f "$marker_path" ]] && previous_hash="$(tr -d '\r\n' < "$marker_path")"
  [[ "$current_hash" == "$previous_hash" ]] && return 0

  if [[ "$optional" == "true" ]]; then
    if "$venv_python" -m pip install -r "$requirements_path"; then
      printf '%s\n' "$current_hash" > "$marker_path"
    else
      printf 'Warning: WhisperX could not be installed; openai-whisper remains available.\n' >&2
    fi
  else
    "$venv_python" -m pip install -r "$requirements_path"
    printf '%s\n' "$current_hash" > "$marker_path"
  fi
}
