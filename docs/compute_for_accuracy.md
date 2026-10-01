# Compute for the next accuracy experiment

Readiness checked on 1 October 2026. This assessment made read-only queries. It did not create a VM, training job, bucket, endpoint, or deployment, and did not enable any service.

## Recommendation

Run the next controlled tabular-model comparison locally first. The supplied workbook contains 2,000 synthetic records, of which 1,400 belong to the official Train split. Each impulse type has only 700 Train records. More compute can compare more candidates, but cannot add independent laboratory evidence or make the source's narrow training ranges representative of unseen equipment. A GPU or a large distributed training cluster has no demonstrated benefit for this experiment.

The useful upgrade is a separately versioned experiment: select and tune each physical target using Train-only cross-validation, normalize model-selection scores by that target's tolerance, compare bounded boosting and smooth residual models, and retain separate calibration records. Preserve the current frozen V1 artifacts and their recorded Hidden Test results. The already exposed Hidden Test must not guide V2 tuning; any subsequent score on it is a reused-test comparison rather than a fresh blind estimate. Obtain fresh measured laboratory trials for the strongest final accuracy claim.

## Observed local resources

| Item | Readiness |
| --- | --- |
| Architecture | ARM64 |
| CPU | 8 physical and 8 logical cores |
| RAM | 8.0 GiB total; approximately 1.46 GiB available during this check |
| Python | 3.12.5 |
| NumPy / scikit-learn | 2.1.3 / 1.7.2 |
| XGBoost | 3.1.2 installed and imports successfully |
| PyTorch | 2.12.1 installed and imports successfully |
| CatBoost / LightGBM | Not installed in the inspected Python environment |

Local resources are sufficient for the present data size. Start with at most two concurrent fits and one or two threads per estimator. Keep the app responsive and avoid nested parallelism. Use a fixed experiment manifest, reproducible seeds, and resumable result files. If a measured pilot shows memory pressure or an unreasonably long search, transfer the same locked experiment to a CPU VM; do not broaden the search merely because credits are available.

## Observed Google Cloud readiness

Google Cloud SDK 586.0.0 is installed. The locally selected project is `fanm-amazonml-2026-01`; successful authenticated read-only queries show billing is enabled. Compute Engine and Cloud Storage APIs are already enabled. The Vertex AI (`aiplatform.googleapis.com`) and Batch APIs are not currently enabled. No region or zone is configured in the inspected CLI configuration.

This project has not been established as the intended hackathon training project. Billing linkage does not verify the user's stated $300 credit balance, expiry, permitted regions, IAM create permissions, resource quotas, or available VM capacity. These remain preflight checks if cloud training becomes necessary. Do not enable extra APIs or select a different billing account simply to run the small local comparison.

App deployment remains deferred. The user's latest authorization permits cloud resources for useful heavy training; it does not require publishing the application.

## Bounded cloud fallback

Use one Linux `e2-standard-4` VM with 4 vCPUs and 16 GiB RAM in `us-central1`, a 20 GiB standard boot disk, and no accelerator. Restrict the experiment to four hours, configure automatic VM deletion with `--max-run-duration=4h` and `--instance-termination-action=DELETE`, and ensure the boot disk is also deleted. Google documents this runtime enforcement, with automatic termination potentially starting up to 30 seconds after the limit. Export checkpoints before the deadline. [Google runtime limits](https://docs.cloud.google.com/compute/docs/instances/limit-vm-runtime)

Reference on-demand USD prices checked on 1 October 2026:

| Item | Four-hour planning estimate |
| --- | --- |
| `e2-standard-4`, Iowa | $0.13402284/hour × 4 = **$0.5361** |
| 20 GiB standard persistent disk, assuming paid usage | $0.000054795/GiB-hour × 20 × 4 = **$0.0044** |
| One ephemeral IPv4 address, assuming paid usage | $0.005/hour × 4 = **$0.0200** |
| Compute, disk, IPv4 subtotal | **Approximately $0.56** |

The VM rate is listed on [Google general-purpose pricing](https://cloud.google.com/products/compute/pricing/general-purpose), the disk rate on [Google disk pricing](https://cloud.google.com/compute/disks-image-pricing), and IPv4 on [Google network pricing](https://cloud.google.com/vpc/network-pricing). These estimates ignore any free allowance and credit discount, and exclude taxes, storage retention, network transfer, logs, or unrelated existing resources. Prices and capacity must be rechecked at launch.

Use a **$5 planning allowance for this entire experiment**, with no automatic retries or additional VMs. A four-hour resource limit bounds the chosen VM's runtime; the allowance is not an account-wide billing cap. Retrieve only the model, predictions, cross-validation records, and manifest; keep transfers small and remove experiment-only storage after retrieval. Preserve the remaining credit for later validation or the explicitly authorized demonstration deployment.

If managed custom training is later preferred, Google supports a single worker-pool custom job, but preparing its package/container and enabling its required services adds setup here. It is not required to improve a 2,000-row tabular benchmark. [Google custom-training documentation](https://docs.cloud.google.com/vertex-ai/docs/training/create-custom-job)

## Evidence required before declaring an accuracy improvement

1. Keep the official Train, Validation, and Hidden Test assignments unchanged.
2. Record model parameters and target-wise selection criteria before viewing any reused-test comparisons.
3. Show errors in microseconds and kilovolts, along with percentage errors and tolerance-normalized errors; avoid a single misleading “accuracy percent.”
4. Report calibration coverage separately from point-prediction error, and flag out-of-distribution settings explicitly.
5. Promote a candidate only on predeclared development criteria and keep V1 reproducible. Fresh measured trials are required for an independent real-equipment claim.

No cloud launch has been performed as part of this assessment.
