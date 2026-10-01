# Google Cloud option

User authorization, updated 1 October 2026: cloud training and heavy compute are authorized within the user's existing $300 Google Cloud credit. Deployment remains on hold until the user explicitly requests it. No cloud resources have been created and no cloud credit has been spent by this build.

The core demo runs entirely offline after installation. For the supplied 2,000 tabular rows, start the controlled accuracy experiments locally and measure their run time before using cloud compute. Use cloud training only if a measured workload warrants it, with a bounded job and spending plan inside the available credit. Additional compute does not substitute for new laboratory data or an untouched evaluation set.

The supplied Dockerfile builds the static Next frontend and serves it with FastAPI from one container. It uses the container's PORT environment variable. A small Cloud Run service is a suitable optional demonstration target; service settings should be chosen only after confirming the intended project and billing account. The currently selected local gcloud project is not assumed to be this hackathon's deployment target.

Suggested initial demonstration settings: two vCPU,1GiB memory, minimum instances0, maximum instances1, concurrency1, request timeout120seconds. These are operating choices, not a price guarantee or spend cap. No GPU is required. Keep the offline laptop available for the final.

## Storage and access limits

The current application has a local SQLite audit store and raw CSVs. On Cloud Run its filesystem is ephemeral: histories can disappear on restart and are not shared across instances. A cloud deployment of this build must be labeled an ephemeral demonstration, must use only synthetic/sample uploads, and should keep invocation restricted to approved viewers. Durable lab history would require persistent object storage plus a database and authentication, which are outside the current local PoC.

The launch recipe below is deliberately parameterized. It is not executed by make/demo and does not select the user's existing project silently.

```sh
gcloud run deploy impulsetwin-demo \
  --source . --project YOUR_CONFIRMED_PROJECT --region asia-south1 \
  --cpu 2 --memory 1Gi --min-instances 0 --max-instances 1 \
  --concurrency 1 --timeout 120 --no-allow-unauthenticated
```

Before deployment, set a dedicated demonstration budget in the confirmed billing account. An alerts-only budget does not stop spending. Google also documents spend-cap budgets; check current eligibility, coverage and enforcement behavior for the chosen account and services rather than assuming alerts are a cap.

Official references checked30September2026:
- [Container port and entrypoint](https://docs.cloud.google.com/run/docs/configuring/services/containers)
- [Maximum instances](https://docs.cloud.google.com/run/docs/configuring/max-instances)
- [Concurrency](https://docs.cloud.google.com/run/docs/configuring/concurrency)
- [Budgets and alerts](https://docs.cloud.google.com/billing/docs/how-to/budgets)
- [Spend-cap budgets](https://docs.cloud.google.com/billing/docs/how-to/budgets-spend-caps)

Container build and Cloud Run deployment must be verified separately; local app success is not a claim of cloud deployment success.
