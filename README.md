<img src="./docs/static/eo-catalogue-logo-1080.webp" align="center" width="200" alt="EO Catalog logo" />

---
EO Catalog, a eoAPI customization.

**Documentation**: <a href="https://eoapi.dev/customization/" target="_blank">https://eoapi.dev/customization/</a>

**Source Code**: <a href="https://github.com/developmentseed/eoapi-devseed" target="_blank">https://github.com/developmentseed/eoapi-devseed</a>

---

This repository shows an example of how users can customize and deploy their own version of eoAPI starting from [eoapi-template](https://github.com/developmentseed/eoapi-template).

## Custom

### Runtimes

#### eoapi.stac

##### Differencing key features

- Add a `TiTilerExtension` and a simple `Search Viewer` (**eoAPI-devseed**)
- Freetext search (**Not yet released - Requires a build of [pgstac](https://github.com/stac-utils/pgstac) from main branch.**)
- Authorization with Openid Connect
- Collection search

When the `TITILER_ENDPOINT` environment variable is set (pointing to the `raster` application) and `titiler` extension is enabled, additional endpoints will be added to the stac-fastapi application:

- `/collections/{collectionId}/items/{itemId}/tilejson.json`: Return the `raster` tilejson for an item
- `/collections/{collectionId}/items/{itemId}/viewer`: Redirect to the `raster` viewer

##### Optimized for performance in high-demand production environments.

- Telemetry for performance measurement.
- Distributed caching.
- Timeout long lasting pending requests.
- Automatic compression of API responses in Brotli, GZIP and Deflate.
- Hide successful health pings from logs (from /_mgmt/ping)

##### Configuration



#### eoapi.raster

The dynamic tiler deployed within `eoapi-devseed` is built on top of [titiler-pgstac](https://github.com/stac-utils/titiler-pgstac) and [pgstac](https://github.com/stac-utils/pgstac). It enables large-scale mosaic based on the results of STAC search queries.

The service includes all the default endpoints from **titiler-pgstac** application and:

- `/`: a custom landing page with links to the different endpoints
- `/mosaic/builder`: a virtual mosaic builder UI that helps create and register STAC Search queries
- `/collections`: a secret (not in OpenAPI documentation) endpoint used in the mosaic-builder page
- `/collections/{collection_id}/items/{item_id}/viewer`: a simple STAC Item viewer

#### eoapi.vector

OGC Features and Tiles API built on top of [tipg](https://github.com/developmentseed/tipg).

The API will look for tables in the database's `public` schema by default. We've also added three functions that connect to the pgSTAC schema:

- **pg_temp.pgstac_collections_view**: Simple function which returns PgSTAC Collections
- **pg_temp.pgstac_hash**: Return features for a specific `searchId` (hash)
- **pg_temp.pgstac_hash_count**: Return the number of items per geometry for a specific `searchId` (hash)

### Infrastructure

The CDK code is almost similar to the one found in [eoapi-template](https://github.com/developmentseed/eoapi-template). We just added some configurations for our custom runtimes.

### Local testing

Before deploying the application on the cloud, you can start by exploring it with a local *Docker* deployment

```
docker compose up
```

Once the applications are *up*, you'll need to add STAC **Collections** and **Items** to the PgSTAC database. If you don't have, you can use the follow the [MAXAR open data demo](https://github.com/vincentsarago/MAXAR_opendata_to_pgstac) (or get inspired by the other [demos](https://github.com/developmentseed/eoAPI/tree/main/demo)).

Then you can start exploring your dataset with:

  - the STAC Metadata service [http://localhost:8081](http://localhost:8081)
  - the Raster service [http://localhost:8082](http://localhost:8082)
  - the browser UI [http://localhost:8085](http://localhost:8085)

If you've added a vector dataset to the `public` schema in the Postgres database, they will be available through the **Vector** service at [http://localhost:8083](http://localhost:8083).

## Deployment

Before getting started, make sure you retrieve all the external dependencies.

```shell
git submodule update --init
```

### Docker

```shell
docker compose up -d
```


### Kubernetes

The repository contains deployment code for hosting this service on Kubernetes through running the published docker image and Helm chart.

> The Helm chart only support the STAC API at the moment.

[EO Catalog Helm Chart](./deploy/helm/eocatalog).

### AWS

#### Requirements

- python >=3.9
- docker
- node >=14
- AWS credentials environment variables configured to point to an account.
- **Optional** a `config.yaml` file to override the default deployment settings defined in `config.py`.

#### Installation

Install python dependencies with

```
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

And node dependencies with

```
npm install
```

Verify that the `cdk` CLI is available. Since `aws-cdk` is installed as a local dependency, you can use the `npx` node package runner tool, that comes with `npm`.

```
npx cdk --version
```

First, synthesize the app

```
npx cdk synth --all
```

Then, deploy

```
npx cdk deploy --all --require-approval never
```

## License

EO Catalog is licensed by [CS GROUP](https://www.csgroup.eu/) under
the [Apache License, version 2.0](http://www.apache.org/licenses/LICENSE-2.0.html).
A copy of this license is provided in the [LICENSE](LICENSE) file.
