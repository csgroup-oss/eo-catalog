## eoapi.stac

![](https://user-images.githubusercontent.com/10407788/151456592-f61ec158-c865-4d98-8d8b-ce05381e0e62.png)

## Configuration

Environment variables to configure EO Catalog STAC API.

### Application configuration

| Name | description | default |
| --- | --- | --- |
| DEBUG | Launch the application in debug mode. | False |
| UI_HREF | If set, add a link URL in collections' metadata to point to its UI representation. | |
| TITILER_ENDPOINT | When set, enable the titiler extension. | "" |
| APP_HOST | IP addresses the server is listening. 0.0.0.0 means all. | 0.0.0.0 |
| APP_PORT | Port exposed by the application. | 8000 |
| APP_ROOT_PATH | Subpath for the STAC API | "" |
| REQUEST_TIMEOUT | Timeout all requests lasting more than the defined duration in seconds. | 30 |

### API configuration

| Name | description | default |
| --- | --- | --- |
| STAC_FASTAPI_TITLE | STAC API title. | stac-fastapi |
| STAC_FASTAPI_DESCRIPTION | STAC API description. | stac-fastapi |
| STAC_FASTAPI_VERSION | STAC API version. | 0.1 |
| STAC_FASTAPI_LANDING_ID | STAC API landing page ID. | stac-fastapi |
| ENABLE_RESPONSE_MODELS | Pydantic validation of server response. | False |
| USE_API_HYDRATE | Perform hydration of stac items within stac-fastapi instead of inside the database. Useful when you want to report more load on the API server instead of the database. | False |
| OPENAPI_URL | Endpoint to expose the API OpenAPI definition. | /api |
| DOCS_URL | Endpoint to expose the API SWAGGER UI | /api.html |

### PostgreSQL database configuration

| Name | description | default |
| --- | --- | --- |
| POSTGRES_USER | Database user. | |
| POSTGRES_PASS | Database password. | |
| POSTGRES_HOST_READER | Hostname of the database read-only service. | |
| POSTGRES_HOST_WRITER | Hostname of the database read-write service. | |
| POSTGRES_PORT | Port of the database. | 5432 |
| POSTGRES_DBNAME | Database name | |
| DB_MIN_CONN_SIZE | Minimum amount of concurrent database connection. | 10 |
| DB_MAX_CONN_SIZE | Maximum amount of concurrent database connection. | 10 |

### Caching configuration

| Name | description | default |
| --- | --- | --- |
| REDIS_HOSTNAME | Hostname for the Redis connection. | |
| REDIS_PASSWORD | Password for the Redis connection | |
| REDIS_PORT | Redis connection port. | 6379 |
| REDIS_SSL | Enforce SSL when connecting to Redis | True |
| REDIS_CLUSTER | Connect to a cluster of Redis instead of a single instance. | False |
| REDIS_TTL | TTL of Redis cache keys in seconds. | 600 |

### Telemetry

| Name | description | default |
| --- | --- | --- |
| OTEL_ENABLED | Enable tracing exporter. | False |
| OTEL_SERVICE_NAME | Service name. | eo-catalog |
| OTEL_EXPORTER_OTLP_TRACES_ENDPOINT | Opentelemetry endpoint for traces. If set override OTEL_EXPORTER_OTLP_ENDPOINT for traces | |

Full Opentelemetry configuration options available from https://opentelemetry.io/docs/languages/sdk-configuration/otlp-exporter/.

### Authentication

The subsequent environment variables are used for the configuration of authentication and authorization for access to collections.

| Name | description                                                                             | default |
| --- |-----------------------------------------------------------------------------------------| --- |
| EOAPI_AUTH_CLIENT_ID | client id used for authentication                                                       | |
| EOAPI_AUTH_OPENID_CONFIGURATION_URL | url to access the openid configuration                                                  | |
| EOAPI_AUTH_USE_PKCE | use Proof Key for Code Exchange                                                         | true |
| EOAPI_AUTH_ALLOWED_JWT_AUDIENCES | allowed JSON web token audiences (has to be set if audience is given in the user token) | |
| EOAPI_AUTH_UPDATE_SCOPE | scope required to update collections and items | admin |
| EOAPI_AUTH_METADATA_FIELD | field where the scope can be found in the collection metadata | scope |
