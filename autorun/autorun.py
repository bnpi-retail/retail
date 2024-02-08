import os
import subprocess
import time

def stop_all_containers():
    try:
        subprocess.run("docker stop $(docker ps -q)", shell=True, check=True)
        print("Успешно остановлены все контейнеры.")
    except subprocess.CalledProcessError as e:
        print(f"Произошла ошибка при остановке контейнеров: {e}")

def are_containers_stopped():
    try:
        result = subprocess.run(["docker", "ps", "-q"], stdout=subprocess.PIPE, check=True, text=True)
        return not result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Произошла ошибка при проверке статуса контейнеров: {e}")
        return False

def start_compose():
    try:
        compose_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "docker-compose.prod.yml"))
        subprocess.run(["docker-compose", "-f", compose_path, "up", "-d"], check=True)
        print("Docker Compose успешно запущен.")
    except subprocess.CalledProcessError as e:
        print(f"Произошла ошибка при запуске Docker Compose: {e}")

stop_all_containers()

while not are_containers_stopped():
    print("Ожидание выключения контейнеров...")
    time.sleep(5)

start_compose()
