# Infraestructura, DevOps, CI/CD, despliegue y operación continua de HYDRA

## 1. Visión general

El proyecto **HYDRA** se ejecutará como una plataforma de micro‑servicios altamente disponible, desplegada en un entorno cloud híbrido (AWS + on‑prem) con infraestructura‑como‑código (IaC) y pipelines de CI/CD totalmente automatizados. Se priorizan los siguientes principios:

- **Escalabilidad**: capacidad de escalar horizontalmente bajo demanda.
- **Resiliencia**: tolerancia a fallos mediante múltiples zonas de disponibilidad.
- **Seguridad**: principio de mínimo privilegio y gestión centralizada de secretos.
- **Observabilidad**: métricas, trazas y logs disponibles en tiempo real.
- **Entrega continua**: despliegues sin tiempo de inactividad y rollback automático.

---

## 2. Topología de infraestructura

| Capa | Tecnologías | Descripción |
|------|--------------|-------------|
| **Red** | VPC, Subnets públicas/privadas, Transit Gateway, Security Groups | Aislamiento de tráfico entre front‑end, workers y bases de datos. |
| **Compute** | Amazon EKS (Kubernetes), EC2 Auto‑Scaling Groups, Fargate | Contenedores para servicios back‑end y batch. Opcional on‑prem con **k3s** para pruebas locales. |
| **Almacenamiento** | Amazon RDS (PostgreSQL), Amazon Aurora, S3 (objetos), EFS (volúmenes compartidos) | Bases de datos relacionales, almacenamiento de artefactos y backups. |
| **Mensajería** | Amazon SQS + SNS, Kafka (confluent) | Colas de trabajo y eventos entre micro‑servicios. |
| **Cache** | Amazon ElastiCache (Redis) | Caché de alta velocidad para sesiones y resultados intermedios. |
| **IAM / Seguridad** | AWS IAM, AWS KMS, HashiCorp Vault | Gestión de roles, políticas y cifrado de secretos. |
| **Observabilidad** | Prometheus, Grafana, Loki, Jaeger, CloudWatch, AWS X‑Ray | Métricas, logs y trazas distribuidas. |
| **CDN** | Amazon CloudFront | Distribución de contenido estático y API Edge. |

---

## 3. Infraestructura como código (IaC)

- **Terraform** como herramienta única para provisionar toda la nube (VPC, EKS, RDS, IAM, S3, etc.).
- Repositorio `infra/terraform` dentro del proyecto **HYDRA**.
- **Terragrunt** para gestionar entornos (`dev`, `stg`, `prd`).
- Módulos reutilizables: `vpc`, `eks`, `rds`, `s3`, `iam`, `networking`.
- **Validaciones** con `terraform validate`, `tflint` y `checkov` en CI.

---

## 4. Pipeline de CI/CD (GitHub Actions)

```
repo: HYDRA
│
├─ .github/workflows/
│   ├─ ci.yml          # Lint, unit tests, security scans
│   ├─ cd-dev.yml      # Deploy a dev cluster (EKS) con Helm
│   ├─ cd-stg.yml      # Deploy a staging cluster y run integration tests
│   └─ cd-prd.yml      # Deploy a production release (manual approval)
```

### CI (ci.yml)
- **Checkout**
- **Setup Python/Node** (versión especificada en `pyproject.toml` / `package.json`).
- **Lint**: `ruff`/`flake8` (Python), `eslint` (JS).
- **Unit Tests**: `pytest` (coverage ≥ 85%).
- **Security**: `bandit`, `npm audit`, `trivy` para imágenes Docker.
- **Build Docker image** & **push** a ECR (tag `sha-${GITHUB_SHA}`).
- **Terraform fmt/validate**.

### CD (cd‑dev.yml, cd‑stg.yml, cd‑prd.yml)
- **Login to AWS** (OIDC federation, no secrets stored).
- **Terraform apply** – plan → apply (auto‑approve for dev, manual for prd).
- **Helm upgrade** del chart `hydra` en el clúster objetivo.
- **Smoke tests** vía `kubectl port-forward` + `pytest‑integration`.
- **Rollback** automático si los tests fallan (helm rollback). 

---

## 5. Estrategia de despliegue

| Tipo | Herramienta | Detalles |
|------|--------------|----------|
| **Blue/Green** | Argo Rollouts (Kubernetes) | Permite validar la nueva versión con tráfico parcial antes del switch final. |
| **Canary** | Flagger + Istio | Incremental rollout con métricas de error‑rate y latency. |
| **Infra‑updates** | Terraform Cloud/ATC | Cambios a la infraestructura son versionados y aprobados vía PR. |
| **Feature toggles** | LaunchDarkly (o `unleash`) | Activación de nuevas funcionalidades sin redeploy. |

---

## 6. Operación continua (Observabilidad & Alertas)

- **Metrics**: Prometheus (scrape de pods) → Grafana dashboards (`service‑latency`, `cpu‑mem‑usage`, `queue‑depth`).
- **Logs**: Loki + Fluent Bit → Grafana Loki; logs también se almacenan en CloudWatch Logs.
- **Tracing**: Jaeger (OTel) para rastrear requests a través de micro‑servicios.
- **Alerting**: Prometheus Alertmanager → PagerDuty / Slack.
- **SLO / SLIs**: Definidos en `docs/operaciones/slo.md` (ej. 99.9% availability, 200 ms latency 95%).
- **Runbooks**: Procedimientos de recuperación (`docs/operaciones/runbooks/`) para incidentes comunes (RDS failover, EKS node drain, secret rotation). 

---

## 7. Seguridad y cumplimiento

- **IAM**: Roles mínimos, políticas separadas por entorno.
- **Secrets**: HashiCorp Vault + `auto‑unseal` con KMS; los pods consumen secretos vía `vault-agent-injector`.
- **Network**: NACLs, Security Groups, WAF (para APIs públicas).
- **Scanning**: Imágenes Docker escaneadas con Trivy; dependencias con Dependabot.
- **Auditoría**: CloudTrail + GuardDuty; logs enviados a S3 con versionado e inspección mediante Athena.
- **Compliance**: ISO‑27001, GDPR – controles definidos en `docs/compliance/`.

---

## 8. Backup y recuperación ante desastres

- **RDS**: snapshots automáticos (daily) + point‑in‑time recovery.
- **EFS/S3**: versionado y replicación cross‑region.
- **EKS**: configuración del cluster guardada en Terraform; `Velero` para backup de volúmenes y recursos k8s.
- **DR Plan**: despliegue en región secundaria (`us-east-2`), con pruebas de failover cada mes.

---

## 9. Gestión de costos

- **Tagging** obligatorio (`project=hydra`, `env=dev|stg|prd`).
- **Budgets** en AWS Budgets → Alertas Slack cuando el gasto mensual supera el 80% del límite.
- **Right‑sizing**: uso de **AWS Compute Optimizer** y `eks‑autoscaler` para ajustar nodos.
- **Spot Instances** para workloads batch con tolerancias a interrupciones.

---

## 10. Roadmap de implementación

| Sprint | Entregable | Comentario |
|-------|------------|-----------|
| 1 | Repo HYDRA creado + estructura de carpetas (`infra/`, `charts/`, `docs/`) | Scaffold inicial. |
| 2 | Terraform VPC + EKS (dev) + CI pipeline (`ci.yml`) | Infra mínima para pruebas. |
| 3 | Helm chart para micro‑servicio `api` + despliegue en dev | Validar CI → CD. |
| 4 | Observabilidad stack (Prometheus, Grafana, Loki) en dev | Dashboard básico. |
| 5 | Canary rollout + alertas de SLO | Pruebas de resiliencia. |
| 6 | Staging environment con aprobaciones manuales | Pruebas integrales. |
| 7 | Production environment + blue/green deployment + backup plan | Go‑live. |
| 8 | Seguridad avanzada (Vault, WAF, auditoría) | Hardening final. |

---

## 11. Referencias

- Terraform AWS Provider docs
- Kubernetes best practices (CNCF)
- GitHub Actions OIDC authentication guide
- AWS Well‑Architected Framework (Reliability, Security, Cost Optimisation)

---

*Este documento será versionado en el repositorio `HYDRA` y sirve como referencia central para los equipos de desarrollo, operaciones y seguridad.*
