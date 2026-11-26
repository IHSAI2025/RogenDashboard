#!/usr/bin/env bash
# 一键管理前后端开发服务：./dev.sh start|stop|restart|status|logs
set -uo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
RUN_DIR="$ROOT_DIR/.run"
LOG_DIR="$ROOT_DIR/logs"
BACKEND_PID_FILE="$RUN_DIR/backend.pid"
FRONTEND_PID_FILE="$RUN_DIR/frontend.pid"
BACKEND_LOG="$LOG_DIR/backend.log"
FRONTEND_LOG="$LOG_DIR/frontend.log"

mkdir -p "$RUN_DIR" "$LOG_DIR"

is_running() {
  local pid_file="$1"
  [[ -f "$pid_file" ]] || return 1
  local pid
  pid="$(cat "$pid_file")"
  [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null
}

# 等日志里出现形如 http://xxx 的地址再打印出来，避免端口被占用时（vite 自动换端口）看不到真实地址
wait_for_url() {
  local log_file="$1" label="$2" timeout="${3:-20}"
  local waited=0 url=""
  while (( waited < timeout )); do
    url="$(grep -m1 -oE 'http://[^[:space:]]+' "$log_file" 2>/dev/null | head -1)"
    if [[ -n "$url" ]]; then
      echo "==> $label 地址: $url"
      return
    fi
    sleep 0.5
    waited=$((waited + 1))
  done
  echo "$label 还未就绪，用 ./dev.sh logs 查看详情"
}

start_backend() {
  if is_running "$BACKEND_PID_FILE"; then
    echo "后端已在运行 (PID $(cat "$BACKEND_PID_FILE"))"
    return
  fi
  : >"$BACKEND_LOG"
  echo "==> 启动后端，日志: $BACKEND_LOG"
  (
    cd "$BACKEND_DIR"
    nohup ./.venv/bin/uvicorn app.main:app --port 8420 --reload \
      >>"$BACKEND_LOG" 2>&1 &
    echo $! >"$BACKEND_PID_FILE"
  )
  wait_for_url "$BACKEND_LOG" "后端"
}

start_frontend() {
  if is_running "$FRONTEND_PID_FILE"; then
    echo "前端已在运行 (PID $(cat "$FRONTEND_PID_FILE"))"
    return
  fi
  : >"$FRONTEND_LOG"
  echo "==> 启动前端，日志: $FRONTEND_LOG"
  (
    cd "$FRONTEND_DIR"
    nohup npm run dev >>"$FRONTEND_LOG" 2>&1 &
    echo $! >"$FRONTEND_PID_FILE"
  )
  wait_for_url "$FRONTEND_LOG" "前端"
}

# 递归收集某个 PID 的所有子孙进程（macOS 没有 setsid，无法用进程组一锅端）
descendants() {
  local pid="$1"
  local children
  children="$(pgrep -P "$pid" 2>/dev/null)"
  for c in $children; do
    descendants "$c"
    echo "$c"
  done
}

kill_port() {
  local port="$1"
  local pids
  pids="$(lsof -ti tcp:"$port" 2>/dev/null)"
  [[ -n "$pids" ]] && kill -TERM $pids 2>/dev/null
}

stop_one() {
  local name="$1" pid_file="$2" port="$3"
  if ! is_running "$pid_file"; then
    echo "$name 未在运行"
    rm -f "$pid_file"
    kill_port "$port"
    return
  fi
  local pid
  pid="$(cat "$pid_file")"
  echo "==> 停止 $name (PID ${pid}, 含子进程)"
  local all_pids
  all_pids="$(descendants "$pid") $pid"
  kill -TERM $all_pids 2>/dev/null
  for _ in $(seq 1 20); do
    kill -0 "$pid" 2>/dev/null || break
    sleep 0.2
  done
  kill -0 "$pid" 2>/dev/null && kill -KILL $all_pids 2>/dev/null
  # 兜底：按端口杀掉可能残留的进程（比如 vite/uvicorn 重新派生过子进程）
  kill_port "$port"
  rm -f "$pid_file"
}

status_one() {
  local name="$1" pid_file="$2"
  if is_running "$pid_file"; then
    echo "$name: 运行中 (PID $(cat "$pid_file"))"
  else
    echo "$name: 未运行"
  fi
}

cmd="${1:-start}"
case "$cmd" in
  start)
    start_backend
    start_frontend
    echo "启动完成。用 ./dev.sh status 查看状态，./dev.sh logs 看日志。"
    ;;
  stop)
    stop_one "后端" "$BACKEND_PID_FILE" 8420
    stop_one "前端" "$FRONTEND_PID_FILE" 5173
    ;;
  restart)
    "$0" stop
    "$0" start
    ;;
  status)
    status_one "后端" "$BACKEND_PID_FILE"
    status_one "前端" "$FRONTEND_PID_FILE"
    ;;
  logs)
    tail -n 50 -f "$BACKEND_LOG" "$FRONTEND_LOG"
    ;;
  *)
    echo "用法: $0 {start|stop|restart|status|logs}"
    exit 1
    ;;
esac
