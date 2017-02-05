# Architecture

## Pods

- Master (Deployment)
    - splunk-master
    - config-backup

- Indexer (StatefulSet)
    - splunk-indexer
    - **TODO** index-backup

## Services

- Master (LoadBalancer) -> Master Pod
    - Exposes Master Pod via external LB

- HttpCollectors (LoadBalancer) -> Indexer Pods
    - Exposes Indexer/HttpCollector Replica Pods via external LB

- Indexers (Headless) -> Indexer Pods
    - Headless Service to provide DNS service discovery for Indexer replica pods

# Initial Setup

## 1. Create ConfigMaps

Create `ConfigMaps` containing bootstrap config for the various Splunk instance roles.

```bash
$ kc create configmap master-boot-config --from-file=master.conf
$ kc create configmap indexer-boot-config --from-file=indexer.conf
```

## 2. Create Secrets

Create the `Secret` volume containing AWS Credentials needed to push config backups to S3.
**credentials** should be an AWS credentials file, such as *~/.aws/credentials*.

```bash
$ cp ~/.aws/credentials .
$ kc create secret generic credentials --from-file=./credentials
```

## 3. Create Master

### Configure Config Backup/Restore variables

TODO

### Create the Splunk Cluster Master/Search Head

```bash
$ kc create -f master-service.yaml -f master-deployment.yaml
```

## 4. Create Indexers

Create the `StatefulSet` and `Services` needed to manage the Indexer cluster.

```bash
$ kc create -f indexer-discovery-service.yaml -f indexer-lb-service.yaml -f indexer-deployment.yaml
```

## 5. Get Master URL

That's it. You now have a fully functional Splunk cluster. Find the URL with which to access the
search head.

```bash
$ kc describe service master | grep "LoadBalancer Ingress"
LoadBalancer Ingress:	**************.us-****-*.elb.amazonaws.com
```

# OPS

## ConfigMaps

### Create

```
kc create configmap indexer-boot-config --from-file=indexer.conf
```

### Update

```
kc create configmap indexer-boot-config --from-file=indexer.conf --dry-run -o yaml | kc replace configmap indexer-boot-config -f -
```

## Secrets

### Create

```
# AWS Credentials needed for pushing config backups to s3
kc create secret generic credentials --from-file=./credentials
```

### Update
```
# AWS Credentials needed for pushing config backups to s3
kc create secret generic credentials --from-file=credentials --dry-run -o yaml | kc replace secret credentials -f -
```
