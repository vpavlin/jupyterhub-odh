# How to deploy the demo JupyterHub

First, log into the cluster and get your project ready

```
oc new-project jupyterhub
```

Then deploy images and prepare the template

```
oc apply -f https://raw.githubusercontent.com/vpavlin/jupyterhub-ocp-oauth/ceph-summit-demo/notebooks.json
oc apply -f https://raw.githubusercontent.com/vpavlin/jupyterhub-ocp-oauth/ceph-summit-demo/templates.json
```

Next is the actual JupyterHub deployment. You can just run with defaults

```
oc process jupyterhub-ocp-oauth | oc apply -f -
```

Or you can change some things - one parameter to make deployments reproducible - i.e. once you get user/password pairs, you can always reuse them; is `HASH_AUTHENTICATOR_SECRET_KEY` - as long as it's same accross deployments, user/password pairs will be the same. If you don't provide it, it's randomly generated.

```
oc process jupyterhub-ocp-oauth HASH_AUTHENTICATOR_SECRET_KEY="meh" | oc apply -f -
```

Wait for the deployment to finish. And access the JupyterHub URL

```
oc get route jupyterhub -o jsonpath={.spec.host}
```

Get some users

```
oc exec $(oc get pods | grep jupyterhub-[0-9] | grep Running | awk '{print $1}') bash generate_users.sh 5
```

Sometimes you may get `500 Internal Error` from JupyterHub server when trying to login. This is due to some race condition with DB start and I did not see a simple way to fix it at the moment. The workaround is to do another deployment/rollout of JupyterHub which forces a restart of the server container and after connecting again to DB, things seem to work fine.

```
oc rollout latest jupyterhub
```