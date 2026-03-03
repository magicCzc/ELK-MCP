"""
Copyright (c) 2025, elk-MCP Project.
All rights reserved.

文件功能：Redis 进程管理工具
用于在 Linux 环境下启动项目私有的 Redis 实例，并处理多进程并发启动冲突。
"""

import subprocess
import time
import logging
import os
import signal
import socket
try:
    import fcntl
except ImportError:
    fcntl = None
from ..config import settings

logger = logging.getLogger(__name__)

class RedisProcessManager:
    _instance = None
    _process = None
    _pidfile = "/tmp/mcp_redis.pid"
    _lockfile = "/tmp/mcp_redis.lock"

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RedisProcessManager, cls).__new__(cls)
        return cls._instance

    def _is_port_open(self) -> bool:
        """检查 Redis 端口是否已被占用"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            return s.connect_ex((settings.REDIS_HOST, settings.REDIS_PORT)) == 0

    def _is_process_running(self, pid: int) -> bool:
        """检查指定 PID 的进程是否在运行"""
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    def start(self):
        """启动私有 Redis 进程（带多进程冲突保护）"""
        if self._process is not None:
            return

        # 1. 检查是否已经有进程在运行
        if os.path.exists(self._pidfile):
            try:
                with open(self._pidfile, "r") as f:
                    old_pid = int(f.read().strip())
                if self._is_process_running(old_pid) and self._is_port_open():
                    logger.info(f"Private Redis is already running (PID: {old_pid})")
                    return
            except (ValueError, OSError):
                pass

        # 2. 尝试获取文件锁以启动进程
        if fcntl:
            lock_f = open(self._lockfile, "w")
            try:
                # 尝试获取排他锁，非阻塞
                fcntl.flock(lock_f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                # 获取锁失败，说明另一个进程正在启动或已启动
                logger.debug("Another process is starting Redis, waiting...")
                time.sleep(2) # 等待启动完成
                if self._is_port_open():
                    return
                else:
                    logger.error("Failed to detect Redis after waiting for another process.")
                    return
        else:
            logger.warning("fcntl not available, skipping file lock (Windows environment?)")
        
        # 3. 再次确认端口是否真的空闲
        if self._is_port_open():
            logger.warning(f"Port {settings.REDIS_PORT} is occupied but no valid pidfile found. Assuming it's already running.")
            lock_f.close()
            return

        # 4. 真正开始启动逻辑
        try:
            import redis_server
            redis_exec = redis_server.REDIS_SERVER_PATH
        except (ImportError, AttributeError):
            redis_exec = "redis-server"

        logger.info(f"Starting private Redis on {settings.REDIS_HOST}:{settings.REDIS_PORT}...")
        
        cmd = [
            redis_exec,
            "--port", str(settings.REDIS_PORT),
            "--bind", settings.REDIS_HOST,
            "--save", "",
            "--appendonly", "no",
            "--daemonize", "no"
        ]

        try:
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid
            )
            
            time.sleep(1.5)
            if self._process.poll() is not None:
                _, stderr = self._process.communicate()
                raise Exception(f"Redis failed to start: {stderr.decode()}")
            
            # 写入 PID 文件
            with open(self._pidfile, "w") as f:
                f.write(str(self._process.pid))
                
            logger.info(f"Private Redis started successfully (PID: {self._process.pid})")
        except Exception as e:
            logger.error(f"Failed to start private Redis: {e}")
            self._process = None
        finally:
            # 释放锁
            if fcntl and 'lock_f' in locals():
                fcntl.flock(lock_f, fcntl.LOCK_UN)
                lock_f.close()

    def stop(self):
        """停止私有 Redis 进程"""
        # 只有启动了进程的那个实例才负责停止（或者最后一个退出的进程）
        # 在多 worker 模式下，通常由主进程管理，或者大家都不管，由 OS 清理
        # 这里我们仅在 self._process 存在时尝试停止
        if self._process:
            logger.info("Stopping private Redis...")
            try:
                os.killpg(os.getpgid(self._process.pid), signal.SIGTERM)
                self._process.wait(timeout=5)
                if os.path.exists(self._pidfile):
                    os.remove(self._pidfile)
            except Exception as e:
                logger.error(f"Error stopping Redis: {e}")
                if self._process:
                    self._process.kill()
            finally:
                self._process = None
                logger.info("Private Redis stopped.")

redis_manager = RedisProcessManager()
