# EO Catalog

This chart bootstraps a [EO Catalog](https://github.com/csgroup-oss/eo-catalog) deployment on a [Kubernetes](http://kubernetes.io) cluster using the [Helm](https://helm.sh) package manager.

## TL;DR

```console
helm install my-release oci://registry-1.docker.io/csgroup-oss/eo-catalog
```

## Prerequisites

- Kubernetes 1.23+
- Helm 3.2.0+
- PV provisioner support in the underlying infrastructure

## Installing the Chart

To install the chart with the release name `my-release`:

```console
helm install my-release oci://registry-1.docker.io/csgroup-oss/eo-catalog
```

These commands deploy EO Catalog on the Kubernetes cluster in the default configuration. The [Parameters](#parameters) section lists the parameters that can be configured during installation.

> **Tip**: List all releases using `helm list`

## Uninstalling the Chart

To uninstall the `my-release` deployment:

```bash
helm uninstall my-release
```

The command removes all the Kubernetes components associated with the chart and deletes the release.

All components are removed except the PrivateVolumeClaim if you use a persistent storage solution.

## Parameters

### Global parameters

| Name                      | Description                                     | Value |
| ------------------------- | ----------------------------------------------- | ----- |
| `global.imageRegistry`    | Global Docker image registry                    | `""`  |
| `global.imagePullSecrets` | Global Docker registry secret names as an array | `[]`  |
| `global.storageClass`     | Global StorageClass for Persistent Volume(s)    | `""`  |

### Common parameters

| Name                | Description                                                          | Value           |
| ------------------- | -------------------------------------------------------------------- | --------------- |
| `kubeVersion`       | Force target Kubernetes version (using Helm capabilities if not set) | `""`            |
| `nameOverride`      | String to partially override common.names.fullname                   | `""`            |
| `fullnameOverride`  | String to fully override common.names.fullname                       | `""`            |
| `namespaceOverride` | String to fully override common.names.namespace                      | `""`            |
| `commonLabels`      | Labels to add to all deployed objects                                | `{}`            |
| `commonAnnotations` | Annotations to add to all deployed objects                           | `{}`            |
| `clusterDomain`     | Kubernetes cluster domain name                                       | `cluster.local` |
| `extraDeploy`       | Array of extra objects to deploy with the release                    | `[]`            |

### EO Catalog STAC API parameters

| Name                                                     | Description                                                                                                                      | Value                                                                                                     |
| -------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| `stac.enabled`                                           | Enabled EO Catalog STAC API                                                                                                      | `true`                                                                                                    |
| `stac.image.registry`                                    | EO Catalog STAC API image registry                                                                                               | `ghcr.io`                                                                                                 |
| `stac.image.repository`                                  | EO Catalog STAC API image repository                                                                                             | `csgroup-oss/eo-catalog-stac`                                                                             |
| `stac.image.tag`                                         | EO Catalog STAC API image tag (immutable tags are recommended)                                                                   | `0.1.0`                                                                                                   |
| `stac.image.digest`                                      | EO Catalog STAC API image digest in the way sha256:aa.... Please note this parameter, if set, will override the tag              | `""`                                                                                                      |
| `stac.image.pullPolicy`                                  | EO Catalog STAC API image pull policy                                                                                            | `IfNotPresent`                                                                                            |
| `stac.image.pullSecrets`                                 | Specify docker-registry secret names as an array                                                                                 | `[]`                                                                                                      |
| `stac.replicaCount`                                      | Number of EO Catalog STAC API replicas                                                                                           | `1`                                                                                                       |
| `stac.appRootPath`                                       | Path for the STAC catalog                                                                                                        | `""`                                                                                                      |
| `stac.host`                                              | IP range STAC Server is listening to                                                                                             | `0.0.0.0`                                                                                                 |
| `stac.api.landingPageId`                                 | id of catalog landing page                                                                                                       | `eo-catalog-stac`                                                                                         |
| `stac.api.title`                                         | title of the catalog landing page                                                                                                | `EO Catalog STAC API`                                                                                     |
| `stac.api.description`                                   | description of the catalog landing page                                                                                          | `Searchable spatiotemporal metadata describing Earth science datasets hosted by the EO Catalog STAC API
` |
| `stac.environment`                                       | Deployment environment. Possible values are development, staging or production                                                   | `production`                                                                                              |
| `stac.debug`                                             | Run the STAC Server in debug mode                                                                                                | `false`                                                                                                   |
| `stac.dbConnectionSize.min`                              | Minimum instances in the database connection pool                                                                                | `1`                                                                                                       |
| `stac.dbConnectionSize.max`                              | Maximum instances in the database connection pool                                                                                | `1`                                                                                                       |
| `stac.initDb`                                            | Run `pypgstac migrate` to initialize the database                                                                                | `true`                                                                                                    |
| `stac.redisTTL`                                          | Disable stac caching in development by setting TTL to 1 second                                                                   | `600`                                                                                                     |
| `stac.redisCluster`                                      | Inform STAC API if connection is set to a Redis Cluster                                                                          | `false`                                                                                                   |
| `stac.useApiHydrate`                                     | Pgcatalog hydration                                                                                                              | `true`                                                                                                    |
| `stac.requestTimeout`                                    |                                                                                                                                  | `30`                                                                                                      |
| `stac.otel.enabled`                                      |                                                                                                                                  | `false`                                                                                                   |
| `stac.otel.serviceName`                                  |                                                                                                                                  | `eo-catalog`                                                                                              |
| `stac.otel.exporterEndpoint`                             |                                                                                                                                  | `nil`                                                                                                     |
| `stac.startupProbe.enabled`                              | Enable startupProbe on EO Catalog STAC API containers                                                                            | `false`                                                                                                   |
| `stac.startupProbe.initialDelaySeconds`                  | Initial delay seconds for startupProbe                                                                                           | `10`                                                                                                      |
| `stac.startupProbe.periodSeconds`                        | Period seconds for startupProbe                                                                                                  | `10`                                                                                                      |
| `stac.startupProbe.timeoutSeconds`                       | Timeout seconds for startupProbe                                                                                                 | `1`                                                                                                       |
| `stac.startupProbe.failureThreshold`                     | Failure threshold for startupProbe                                                                                               | `3`                                                                                                       |
| `stac.startupProbe.successThreshold`                     | Success threshold for startupProbe                                                                                               | `1`                                                                                                       |
| `stac.livenessProbe.enabled`                             | Enable livenessProbe on EO Catalog STAC API containers                                                                           | `true`                                                                                                    |
| `stac.livenessProbe.initialDelaySeconds`                 | Initial delay seconds for livenessProbe                                                                                          | `3`                                                                                                       |
| `stac.livenessProbe.periodSeconds`                       | Period seconds for livenessProbe                                                                                                 | `10`                                                                                                      |
| `stac.livenessProbe.timeoutSeconds`                      | Timeout seconds for livenessProbe                                                                                                | `1`                                                                                                       |
| `stac.livenessProbe.failureThreshold`                    | Failure threshold for livenessProbe                                                                                              | `3`                                                                                                       |
| `stac.livenessProbe.successThreshold`                    | Success threshold for livenessProbe                                                                                              | `1`                                                                                                       |
| `stac.readinessProbe.enabled`                            | Enable readinessProbe on EO Catalog STAC API containers                                                                          | `true`                                                                                                    |
| `stac.readinessProbe.initialDelaySeconds`                | Initial delay seconds for readinessProbe                                                                                         | `3`                                                                                                       |
| `stac.readinessProbe.periodSeconds`                      | Period seconds for readinessProbe                                                                                                | `10`                                                                                                      |
| `stac.readinessProbe.timeoutSeconds`                     | Timeout seconds for readinessProbe                                                                                               | `1`                                                                                                       |
| `stac.readinessProbe.failureThreshold`                   | Failure threshold for readinessProbe                                                                                             | `3`                                                                                                       |
| `stac.readinessProbe.successThreshold`                   | Success threshold for readinessProbe                                                                                             | `1`                                                                                                       |
| `stac.customLivenessProbe`                               | Custom livenessProbe that overrides the default one                                                                              | `{}`                                                                                                      |
| `stac.customReadinessProbe`                              | Custom readinessProbe that overrides the default one                                                                             | `{}`                                                                                                      |
| `stac.resources.limits`                                  | The resources limits for the EO Catalog STAC API containers                                                                      | `{}`                                                                                                      |
| `stac.resources.requests`                                | The requested resources for the EO Catalog STAC API containers                                                                   | `{}`                                                                                                      |
| `stac.horizontalPodAutoscaler.enabled`                   | Decide to enable or disable the horizontal pod autoscaler                                                                        | `false`                                                                                                   |
| `stac.horizontalPodAutoscaler.maxReplicas`               | The maximum number of replicas that are allowed to run simultaneously                                                            | `10`                                                                                                      |
| `stac.horizontalPodAutoscaler.cpuUtilization`            | The maximum CPU utilization target computed in % of the CPU resources request.                                                   | `50`                                                                                                      |
| `stac.horizontalPodAutoscaler.memUtilization`            | The maximum RAM utilization target computed in % of the RAM resources request.                                                   | `50`                                                                                                      |
| `stac.podSecurityContext.enabled`                        | Enabled EO Catalog STAC API pods' Security Context                                                                               | `true`                                                                                                    |
| `stac.podSecurityContext.fsGroup`                        | Set EO Catalog STAC API pod's Security Context fsGroup                                                                           | `1001`                                                                                                    |
| `stac.containerSecurityContext.enabled`                  | Enabled EO Catalog STAC API containers' Security Context                                                                         | `true`                                                                                                    |
| `stac.containerSecurityContext.runAsUser`                | Set EO Catalog STAC API containers' Security Context runAsUser                                                                   | `1001`                                                                                                    |
| `stac.containerSecurityContext.allowPrivilegeEscalation` | Set EO Catalog STAC API containers' Security Context allowPrivilegeEscalation                                                    | `false`                                                                                                   |
| `stac.containerSecurityContext.capabilities.drop`        | Set EO Catalog STAC API containers' Security Context capabilities to be dropped                                                  | `["all"]`                                                                                                 |
| `stac.containerSecurityContext.readOnlyRootFilesystem`   | Set EO Catalog STAC API containers' Security Context readOnlyRootFilesystem                                                      | `false`                                                                                                   |
| `stac.containerSecurityContext.runAsNonRoot`             | Set EO Catalog STAC API container's Security Context runAsNonRoot                                                                | `true`                                                                                                    |
| `stac.command`                                           | Override default container command (useful when using custom images)                                                             | `[]`                                                                                                      |
| `stac.args`                                              | Override default container args (useful when using custom images). Overrides the defaultArgs.                                    | `[]`                                                                                                      |
| `stac.containerPorts.http`                               | EO Catalog STAC API application HTTP port number                                                                                 | `8080`                                                                                                    |
| `stac.hostAliases`                                       | EO Catalog STAC API pods host aliases                                                                                            | `[]`                                                                                                      |
| `stac.podLabels`                                         | Extra labels for EO Catalog STAC API pods                                                                                        | `{}`                                                                                                      |
| `stac.podAnnotations`                                    | Annotations for EO Catalog STAC API pods                                                                                         | `{}`                                                                                                      |
| `stac.podAffinityPreset`                                 | Pod affinity preset. Ignored if `affinity` is set. Allowed values: `soft` or `hard`                                              | `""`                                                                                                      |
| `stac.podAntiAffinityPreset`                             | Pod anti-affinity preset. Ignored if `affinity` is set. Allowed values: `soft` or `hard`                                         | `soft`                                                                                                    |
| `stac.nodeAffinityPreset.type`                           | Node affinity preset type. Ignored if `affinity` is set. Allowed values: `soft` or `hard`                                        | `""`                                                                                                      |
| `stac.nodeAffinityPreset.key`                            | Node label key to match. Ignored if `affinity` is set                                                                            | `""`                                                                                                      |
| `stac.nodeAffinityPreset.values`                         | Node label values to match. Ignored if `affinity` is set                                                                         | `[]`                                                                                                      |
| `stac.affinity`                                          | Affinity for EO Catalog STAC API pods assignment                                                                                 | `{}`                                                                                                      |
| `stac.nodeSelector`                                      | Node labels for EO Catalog STAC API pods assignment                                                                              | `{}`                                                                                                      |
| `stac.tolerations`                                       | Tolerations for EO Catalog STAC API pods assignment                                                                              | `[]`                                                                                                      |
| `stac.schedulerName`                                     | Name of the k8s scheduler (other than default)                                                                                   | `""`                                                                                                      |
| `stac.shareProcessNamespace`                             | Enable shared process namespace in a pod.                                                                                        | `false`                                                                                                   |
| `stac.topologySpreadConstraints`                         | Topology Spread Constraints for pod assignment                                                                                   | `[]`                                                                                                      |
| `stac.updateStrategy.type`                               | EO Catalog STAC API statefulset strategy type                                                                                    | `RollingUpdate`                                                                                           |
| `stac.priorityClassName`                                 | EO Catalog STAC API pods' priorityClassName                                                                                      | `""`                                                                                                      |
| `stac.runtimeClassName`                                  | Name of the runtime class to be used by pod(s)                                                                                   | `""`                                                                                                      |
| `stac.lifecycleHooks`                                    | for the EO Catalog STAC API container(s) to automate configuration before or after startup                                       | `{}`                                                                                                      |
| `stac.extraEnvVars`                                      | Array with extra environment variables to add to EO Catalog STAC API nodes                                                       | `[]`                                                                                                      |
| `stac.extraEnvVarsCM`                                    | Name of existing ConfigMap containing extra env vars for EO Catalog STAC API nodes                                               | `""`                                                                                                      |
| `stac.extraEnvVarsSecret`                                | Name of existing Secret containing extra env vars for EO Catalog STAC API nodes                                                  | `""`                                                                                                      |
| `stac.extraVolumes`                                      | Optionally specify extra list of additional volumes for the EO Catalog STAC API pod(s)                                           | `[]`                                                                                                      |
| `stac.extraVolumeMounts`                                 | Optionally specify extra list of additional volumeMounts for the EO Catalog STAC API container(s)                                | `[]`                                                                                                      |
| `stac.sidecars`                                          | Add additional sidecar containers to the EO Catalog STAC API pod(s)                                                              | `[]`                                                                                                      |
| `stac.initContainers`                                    | Add additional init containers to the EO Catalog STAC API pod(s)                                                                 | `[]`                                                                                                      |
| `stac.service.type`                                      | Kubernetes service type                                                                                                          | `ClusterIP`                                                                                               |
| `stac.service.http.enabled`                              | Enable http port on service                                                                                                      | `true`                                                                                                    |
| `stac.service.ports.http`                                | EO Catalog STAC API service HTTP port                                                                                            | `8080`                                                                                                    |
| `stac.service.nodePorts`                                 | Specify the nodePort values for the LoadBalancer and NodePort service types.                                                     | `{}`                                                                                                      |
| `stac.service.sessionAffinity`                           | Control where client requests go, to the same pod or round-robin                                                                 | `None`                                                                                                    |
| `stac.service.sessionAffinityConfig`                     | Additional settings for the sessionAffinity                                                                                      | `{}`                                                                                                      |
| `stac.service.clusterIP`                                 | EO Catalog STAC API service clusterIP IP                                                                                         | `""`                                                                                                      |
| `stac.service.loadBalancerIP`                            | loadBalancerIP for the SuiteCRM Service (optional, cloud specific)                                                               | `""`                                                                                                      |
| `stac.service.loadBalancerSourceRanges`                  | Address that are allowed when service is LoadBalancer                                                                            | `[]`                                                                                                      |
| `stac.service.externalTrafficPolicy`                     | Enable client source IP preservation                                                                                             | `Cluster`                                                                                                 |
| `stac.service.annotations`                               | Additional custom annotations for EO Catalog STAC API service                                                                    | `{}`                                                                                                      |
| `stac.service.extraPorts`                                | Extra port to expose on EO Catalog STAC API service                                                                              | `[]`                                                                                                      |
| `stac.ingress.enabled`                                   | Enable the creation of an ingress for the EO Catalog STAC API                                                                    | `false`                                                                                                   |
| `stac.ingress.pathType`                                  | Path type for the EO Catalog STAC API ingress                                                                                    | `ImplementationSpecific`                                                                                  |
| `stac.ingress.apiVersion`                                | Ingress API version for the EO Catalog STAC API ingress                                                                          | `""`                                                                                                      |
| `stac.ingress.hostname`                                  | Ingress hostname for the EO Catalog STAC API ingress                                                                             | `eo-catalog-stac-api.local`                                                                               |
| `stac.ingress.annotations`                               | Annotations for the EO Catalog STAC API ingress. To enable certificate autogeneration, place here your cert-manager annotations. | `{}`                                                                                                      |
| `stac.ingress.tls`                                       | Enable TLS for the EO Catalog STAC API ingress                                                                                   | `false`                                                                                                   |
| `stac.ingress.extraHosts`                                | Extra hosts array for the EO Catalog STAC API ingress                                                                            | `[]`                                                                                                      |
| `stac.ingress.path`                                      | Path array for the EO Catalog STAC API ingress                                                                                   | `/`                                                                                                       |
| `stac.ingress.extraPaths`                                | Extra paths for the EO Catalog STAC API ingress                                                                                  | `[]`                                                                                                      |
| `stac.ingress.extraTls`                                  | Extra TLS configuration for the EO Catalog STAC API ingress                                                                      | `[]`                                                                                                      |
| `stac.ingress.secrets`                                   | Secrets array to mount into the Ingress                                                                                          | `[]`                                                                                                      |
| `stac.ingress.ingressClassName`                          | IngressClass that will be be used to implement the Ingress (Kubernetes 1.18+)                                                    | `""`                                                                                                      |
| `stac.ingress.selfSigned`                                | Create a TLS secret for this ingress record using self-signed certificates generated by Helm                                     | `false`                                                                                                   |
| `stac.ingress.extraRules`                                | Additional rules to be covered with this ingress record                                                                          | `[]`                                                                                                      |
| `stac.serviceAccount.create`                             | Specifies whether a ServiceAccount should be created                                                                             | `true`                                                                                                    |
| `stac.serviceAccount.name`                               | The name of the ServiceAccount to use.                                                                                           | `""`                                                                                                      |
| `stac.serviceAccount.annotations`                        | Additional custom annotations for the ServiceAccount                                                                             | `{}`                                                                                                      |
| `stac.serviceAccount.automountServiceAccountToken`       | Automount service account token for the server service account                                                                   | `true`                                                                                                    |
| `stac.redisWait.enabled`                                 | Enables waiting for redis                                                                                                        | `true`                                                                                                    |
| `stac.redisWait.extraArgs`                               | Additional arguments for the redis-cli call, such as TLS                                                                         | `""`                                                                                                      |
| `stac.redisWait.securityContext`                         | Security context for init container                                                                                              | `{}`                                                                                                      |

### EO Catalog PostgreSQL parameters

| Name                                | Description                                                                                                       | Value          |
| ----------------------------------- | ----------------------------------------------------------------------------------------------------------------- | -------------- |
| `postgresql.enabled`                | Switch to enable or disable the PostgreSQL helm chart                                                             | `true`         |
| `postgresql.auth.postgresPassword`  | Password for the "postgres" admin user. Ignored if `auth.existingSecret` with key `postgres-password` is provided | `""`           |
| `postgresql.auth.username`          | Name for a custom user to create                                                                                  | `eo-catalog` |
| `postgresql.auth.password`          | Password for the custom user to create                                                                            | `""`           |
| `postgresql.auth.database`          | Name for a custom database to create                                                                              | `postgis`      |
| `postgresql.auth.existingSecret`    | Name of existing secret to use for PostgreSQL credentials                                                         | `""`           |
| `postgresql.architecture`           | PostgreSQL architecture (`standalone` or `replication`)                                                           | `standalone`   |
| `postgresql.primary.initdb.scripts` | Dictionary of initdb scripts                                                                                      | `{}`           |

### EO Catalog Redis parameters

| Name                                   | Description                                                            | Value            |
| -------------------------------------- | ---------------------------------------------------------------------- | ---------------- |
| `redis.enabled`                        | Enable Redis dependency                                                | `true`           |
| `redis.nameOverride`                   | Name override for the Redis dependency                                 | `""`             |
| `redis.service.port`                   | Service port for Redis dependency                                      | `6379`           |
| `redis.auth.enabled`                   | Enable Redis dependency authentication                                 | `true`           |
| `redis.auth.existingSecret`            | Existing secret to load redis dependency password                      | `""`             |
| `redis.auth.existingSecretPasswordKey` | Pasword key name inside the existing secret                            | `redis-password` |
| `redis.architecture`                   | Redis&reg; architecture. Allowed values: `standalone` or `replication` | `standalone`     |
| `redis.tls.enabled`                    | Enable TLS traffic                                                     | `false`          |

### EO Catalog external database parameters

| Name                                                 | Description                                                                                                         | Value          |
| ---------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- | -------------- |
| `externalDatabase.host`                              | Database host                                                                                                       | `""`           |
| `externalDatabase.hostWriter`                        | Database host for write operations. Default to externalDatabase.host. Needed when externalDatabase.host is readonly | `""`           |
| `externalDatabase.port`                              | Database port number                                                                                                | `5432`         |
| `externalDatabase.user`                              | Non-root username for EO Catalog STAC API                                                                           | `eo-catalog` |
| `externalDatabase.password`                          | Password for the non-root username for EO Catalog STAC API                                                          | `""`           |
| `externalDatabase.postgresPassword`                  | Password for the root username for EO Catalog STAC API                                                              | `""`           |
| `externalDatabase.database`                          | EO Catalog STAC API database name                                                                                   | `postgis`      |
| `externalDatabase.existingSecret`                    | Name of an existing secret resource containing the database credentials                                             | `""`           |
| `externalDatabase.existingSecretPasswordKey`         | Name of an existing secret key containing the database credentials                                                  | `""`           |
| `externalDatabase.existingSecretPostgresPasswordKey` | Name of an existing secret key containing the database postgres credentials                                         | `""`           |

### EO Catalog external Redis parameters

| Name                                      | Description                                                                 | Value            |
| ----------------------------------------- | --------------------------------------------------------------------------- | ---------------- |
| `externalRedis.host`                      | External Redis host                                                         | `""`             |
| `externalRedis.port`                      | External Redis port                                                         | `6379`           |
| `externalRedis.password`                  | External Redis password                                                     | `""`             |
| `externalRedis.existingSecret`            | Existing secret for the external redis                                      | `""`             |
| `externalRedis.existingSecretPasswordKey` | Password key for the existing secret containing the external redis password | `redis-password` |
| `externalRedis.tlsEnabled`                | Enable TLS traffic                                                          | `false`          |

## Configuration and installation details

```console
$ helm install my-release \
  --set image.pullPolicy=Always \
    my-repo/eo-catalog
```

The above command sets the `image.pullPolicy` to `Always`.

Alternatively, a YAML file that specifies the values for the parameters can be provided while installing the chart. For example,

```console
helm install my-release -f values.yaml my-repo/eo-catalog
```

> **Tip**: You can use the default [values.yaml](values.yaml)

### [Rolling VS Immutable tags](https://docs.bitnami.com/containers/how-to/understand-rolling-tags-containers/)

It is strongly recommended to use immutable tags in a production environment. This ensures your deployment does not change automatically if the same tag is updated with a different image.

CS Group will release a new chart updating its containers if a new version of the main containers, significant changes, or critical vulnerabilities exist.
