# Changelog

## 1.1.0

- use Django's `connection.execute_wrapper` for SQL logging

## 1.2.0

- add s3 utils for django package

## 1.3.0

- add CdnBulkStaticStorage class to django package

## 1.3.1

- add utility management commands for s3 utils

## 1.5.1

- change the use of Django's `connection.execute_wrapper` to `connections[db_name].execute_wrapper` for SQL logging on
  non-default dbs

## 1.5.2

- TODO

## 1.6.0

- add class `SmartRetryHTTPAdapter`

## 1.6.1

- use a single point of return with a single log line in a fixed format in `SmartRetryHTTPAdapter.send`

## 1.8.0

- add `retry` decorator for retrying functions on exception with configurable delay, backoff and jitter

## 1.7.0

- add queryset batching: `batch_ordered_queryset` and `iterate_batch_ordered_queryset`

## 1.8.5

- retry dropped connections in `SmartRetryHTTPAdapter`

## 1.8.6

- don't retry in `SmartRetryHTTPAdapter` when running tests

## 1.9.0

- add `GracefulCommand` (`baumbelt.django.cmd`) for SIGTERM-aware management commands
- add `baumbelt.django.db` app with `wait_for_migrations`/`wait-for-migrations` command
- **breaking:** `wait-for-migrations` moved from `baumbelt.django.s3utils` to `baumbelt.django.db` — add
  `"baumbelt.django.db"` to `INSTALLED_APPS` instead
- add `baumbelt.django.procs` app with `show-running-management-commands` command
- add `delete_unreferenced_files` to `baumbelt.django.s3utils.utils`
- add `loop_log` to `baumbelt.logs`

## 1.9.1

- `GracefulCommand` skips `wait_for_migrations` under a test runner — mirrors the 1.8.6 `SmartRetryHTTPAdapter` fix.
  Without it, per-`TestCase` DB isolation makes the migrate-check fail forever, blocking the command for the full 60s
  timeout.
