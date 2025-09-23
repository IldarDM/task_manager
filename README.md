# Task Manager API

[![Python](https://img.shields.io/badge/python-3.12-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.101.0-green)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7-red)](https://redis.io/)

**Task Manager** — это RESTful API для управления задачами.  
Проект построен на **FastAPI**, использует **PostgreSQL** и **Redis**, полностью работает через **Docker**, с тестами и поддержкой **Swagger**-документации.  

Проект является частью комплексной экосистемы для управления задачами, которая будет включать:  
- **REST API** — основной бэкенд для управления пользователями, задачами и категориями.  
- **Telegram-бот** — пользовательский интерфейс для взаимодействия с задачами через мессенджер.  
- **MCP** - для взаимодействия LLM с сервисом. 
---

## 🔹 Основные возможности

- **Аутентификация и авторизация**  
  - JWT токены  
  - Регистрация, логин, профиль пользователя  
  - Обновление данных пользователя  

- **Задачи (Tasks)**  
  - CRUD операции  
  - Фильтры по статусу, приоритету, категории и срокам  
  - Пагинация и сортировка  
  - Soft delete, восстановление и архивирование задач  
  - Статистика задач  

- **Категории (Categories)**  
  - CRUD операции  
  - Дефолтная категория `Uncategorized` для каждого пользователя  
  - Подсчёт задач в категории  

- **Дополнительно**  
  - Rate limiting через Redis  
  - Email уведомления через SMTP  
  - Swagger-документация при `DEBUG=True`  

---

## 🔹 Технологии

- Python 3.12  
- FastAPI  
- PostgreSQL + SQLAlchemy  
- Redis  
- Pydantic  
- Docker & Docker Compose  
- Pytest + Faker для тестирования  

---

## 🔹 Быстрый старт (Docker)

### 1. Клонируем репозиторий

```bash
git clone <repository-url>
cd task_manager
```
### 2. Создаём Docker-сеть

```bash
docker network create task_manager_network
```
### 3. Запуск основной среды

```bash
docker-compose up -d --build
```

Backend: http://localhost:8000

Swagger: http://localhost:8000/docs
 (при DEBUG=True)

### 4. Остановка

```bash
docker-compose down
```

## 🔹 Тестирование

Используется отдельное тестовое окружение:

```bash
docker-compose -f docker-compose.test.yml up --build
```

Тесты запускаются автоматически внутри контейнера backend_test

Redis и Postgres очищаются между тестами

Используется .env.test

## 🔹 Сжатая спецификация API

### Auth
| Метод | Путь | Описание | Ответ |
|-------|------|----------|-------|
| POST | `/api/v1/auth/register` | Регистрация нового пользователя | `UserResponse` |
| POST | `/api/v1/auth/login` | Логин пользователя | `Token` |
| GET  | `/api/v1/auth/me` | Получение данных текущего пользователя | `UserResponse` |
| POST | `/api/v1/auth/logout` | Выход пользователя | `SuccessResponse` |

### Tasks
| Метод | Путь | Параметры | Ответ |
|-------|------|-----------|-------|
| GET  | `/api/v1/tasks` | query: `status`, `priority`, `search`, `sort`, `limit`, `skip` | `List[TaskResponse]` |
| POST | `/api/v1/tasks` | `TaskCreate` | `TaskResponse` |
| GET  | `/api/v1/tasks/{id}` | — | `TaskResponse` |
| PUT  | `/api/v1/tasks/{id}` | `TaskUpdate` | `TaskResponse` |
| DELETE | `/api/v1/tasks/{id}` | — | `SuccessResponse` |
| POST | `/api/v1/tasks/{id}/archive` | — | `TaskResponse` |
| POST | `/api/v1/tasks/{id}/restore` | — | `TaskResponse` |
| GET  | `/api/v1/tasks/stats/overview` | — | `Stats` |

### Categories
| Метод | Путь | Параметры | Ответ |
|-------|------|-----------|-------|
| GET  | `/api/v1/categories` | — | `List[CategoryResponse]` |
| POST | `/api/v1/categories` | `CategoryCreate` | `CategoryResponse` |
| GET  | `/api/v1/categories/{id}` | — | `CategoryResponse` |
| PUT  | `/api/v1/categories/{id}` | `CategoryUpdate` | `CategoryResponse` |
| DELETE | `/api/v1/categories/{id}` | — | `SuccessResponse` |
| GET  | `/api/v1/categories/{id}/tasks` | — | `List[TaskResponse]` |

> ⚠️ Swagger документация доступна при включенном `DEBUG=True` в `.env`.
