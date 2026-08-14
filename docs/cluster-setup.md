# Cluster setup: getting a real OpenShift to practise on

Hands-on questions are graded against a **real OpenShift cluster** using
`oc`. You have three options, easiest first.

## 1. Red Hat OpenShift Local (CRC) — recommended

A single-node OpenShift 4.x VM that runs on your workstation/lab host.

- Requires: 4 vCPU, ~9 GB free RAM, KVM (Linux) or Hyper-V/VirtualBox, a free
  Red Hat account and pull secret.
- Get it: <https://developers.redhat.com/products/openshift-local> (download
  the `crc` binary + bundle).

```bash
./cluster/preflight.sh          # confirm the host can do it
./cluster/crc.sh setup          # crc setup + start with your pull secret
./cluster/crc.sh login          # prints console URL + oc login + kubeconfig
oc login -u kubeadmin ...       # or: export KUBECONFIG=$HOME/.crc/machines/crc/kubeconfig
```

Once `oc` works from the shell, the simulator's **conductor** can grade
hands-on tasks: run it on the same host (`GA_CLUSTER=local`) or on another
machine via SSH (`GA_CLUSTER=remote://user@host`).

## 2. OKD (community OpenShift)

The upstream community distribution, ~same API surface as OpenShift 4.
Two viable routes:

- **Single-node (SNO)** install with `openshift-install` — needs DNS records
  for `api.<cluster>.<base>` and `*.apps.<cluster>.<base>` pointing at your
  host, and a network you can shape.
- **Existing virtualization**: an OKD VM is a fine practice target for the
  EX288 developer tasks; administration tasks (SCCs, operators) also work.

```bash
./cluster/okd.sh fetch-tools      # openshift-install + oc, 4.17 stable
./cluster/okd.sh install-config   # write the template, then edit it
openshift-install create cluster --dir cluster/okd-install
```

Expect ~1-2 hours on capable hardware, mostly waiting for the cluster to
become ready.

## 3. A shared/remote cluster

If you have access to an existing OpenShift cluster (a workplace lab, or a
public playground) you can point the simulator at it:

- Put a kubeconfig that reaches the cluster where the **conductor** can read
  it (`~/.kube/config` for the local backend).
- For a remote cluster host, use `GA_CLUSTER=remote://user@host`.

> Practice only. Do not run the simulator's grading against a production
> cluster — hands-on checks run real commands against the API server.

## After the cluster is up

1. Verify: `oc get nodes` (1 Ready node for CRC).
2. Log in: the default `kubeadmin` user or your htpasswd user.
3. Start the platform UI and take an attempt. In **Training** mode you can
   read solutions while you work. In **Exam** mode the timer runs.
