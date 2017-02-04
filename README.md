# Architecture

## Pods

- Master (Deployment)
    - splunk-master
    - config-backup

- Indexer (StatefulSet)
    - splunk-indexer
    - index-backup

## Services

- Master (LoadBalancer) -> Master Pod
    - Exposes Master Pod via external LB

- HttpCollectors (LoadBalancer) -> Indexer Pods
    - Exposes Indexer/HttpCollector Replica Pods via external LB

- Indexers (Headless) -> Indexer Pods
    - Headless Service to provide DNS service discovery for Indexer replica pods

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
# AWS Credentials
kc create secret generic credentials --from-file=./credentials
```

### Update
```
# AWS Credentials
kc create secret generic credentials --from-file=credentials --dry-run -o yaml | kc replace secret credentials -f -
```
