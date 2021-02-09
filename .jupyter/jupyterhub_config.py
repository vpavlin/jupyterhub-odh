c.KubeSpawner.http_timeout = 60 * 10 #Images are big, take time to pull, make it 10 mins for now because of storage issue
c.KubeSpawner.start_timeout = 60 * 10 #Images are big, take time to pull, make it 10 mins for now because of storage issue

import os
import sys

import json
import requests

c.JupyterHub.log_level = 'DEBUG'
# Do not shut down singleuser servers on restart
c.JupyterHub.cleanup_servers = False


import uuid
c.ConfigurableHTTPProxy.auth_token = str(uuid.uuid4())
public_service_dict = {
                        'PROXY_TOKEN': c.ConfigurableHTTPProxy.auth_token,
                        'PROXY_API_URL': 'http://%s:%d/' % ("127.0.0.1", 8082)
                    }
public_service_dict.update(os.environ)
jsp_api_dict = {
    'KUBERNETES_SERVICE_HOST': os.environ['KUBERNETES_SERVICE_HOST'],
    'KUBERNETES_SERVICE_PORT': os.environ['KUBERNETES_SERVICE_PORT']
}
c.JupyterHub.services = [
                            {
                                'name': 'public',
                                'command': ['bash', '-c', 'jupyter_publish_service'],
                                'environment': public_service_dict
                            },
                            {
                                'name': 'jsp-api',
                                'url': 'http://127.0.0.1:8181',
                                'admin': True,
                                'command': ['jupyterhub-singleuser-profiles-api'],
                                'environment': jsp_api_dict
                            }
                        ]

DEFAULT_MOUNT_PATH = '/opt/app-root/src'

c.KubeSpawner.singleuser_extra_containers = [
        {
            "name": "nbviewer",
            "image": "nbviewer:latest",
            "ports": [
                {
                    "containerPort": 9090,
                    "protocol": "TCP"
                }
            ],
            "env" : [
                {
                    "name": "NBVIEWER_LOCALFILES",
                    "value": "/opt/app-root/src/public_notebooks"
                },
                {
                    "name": "NBVIEWER_TEMPLATES",
                    "value": "/opt/app-root/src"
                },
                {
                    "name": "NBVIEWER_PORT",
                    "value": "9090"
                },
                {
                    "name": "JUPYTERHUB_SERVICE_PREFIX",
                    "value": "/user/{username}/public/"
                },
                {
                    "name": "CACHE_EXPIRY_MIN",
                    "value": "30"
                },
                {
                    "name": "CACHE_EXPIRY_MAX",
                    "value": "60"
                },
                {
                    "name": "NO_CACHE",
                    "value": "true"
                }
            ],
        "volumeMounts": [
            {
                "mountPath": DEFAULT_MOUNT_PATH,
                "name": "data"
            }
        ]
        }
    ]


# Work out the public server address for the OpenShift REST API. Don't
# know how to get this via the REST API client so do a raw request to
# get it. Make sure request is done in a session so connection is closed
# and later calls against REST API don't attempt to reuse it. This is
# just to avoid potential for any problems with connection reuse.

# Enable the OpenShift authenticator.

from oauthenticator.openshift import OpenShiftOAuthenticator
c.JupyterHub.authenticator_class = OpenShiftOAuthenticator

# Override scope as oauthenticator code doesn't set it correctly.
# Need to lodge a PR against oauthenticator to have this fixed.

#OpenShiftOAuthenticator.scope = ['user:info']

# Setup authenticator configuration using details from environment.

service_name = os.environ['JUPYTERHUB_SERVICE_NAME']

service_account_name = '%s-hub' %  service_name
service_account_path = '/var/run/secrets/kubernetes.io/serviceaccount'

with open(os.path.join(service_account_path, 'namespace')) as fp:
    namespace = fp.read().strip()

client_id = 'system:serviceaccount:%s:%s' % (namespace, service_account_name)

c.OpenShiftOAuthenticator.client_id = client_id

with open(os.path.join(service_account_path, 'token')) as fp:
    client_secret = fp.read().strip()

c.OpenShiftOAuthenticator.client_secret = client_secret
c.OpenShiftOAuthenticator.allowed_groups = ['odh-users', 'odh-admins']
c.OpenShiftOAuthenticator.admin_groups = ['odh-admins']

# Work out hostname for the exposed route of the JupyterHub server. This
# is tricky as we need to use the REST API to query it.

verify_ssl = False

from kubernetes import client, config
from openshift.dynamic import DynamicClient

config.load_incluster_config()

configuration = client.Configuration()
configuration.verify_ssl = verify_ssl

oapi_client = DynamicClient(
    client.ApiClient(configuration=configuration)
)

routes = oapi_client.resources.get(kind='Route', api_version='route.openshift.io/v1')

route_list = routes.get(namespace=namespace)

host = None

for route in route_list.items:
    if route.metadata.name == service_name:
        host = route.spec.host

if not host:
    raise RuntimeError('Cannot calculate external host name for JupyterHub.')

c.OpenShiftOAuthenticator.oauth_callback_url = 'https://%s/hub/oauth_callback' % host

from html.parser import HTMLParser

class UILinkParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.data = None
        self.tag = None
        self.attrs = None
        self.result = []
        self.html_tag = []

    def handle_starttag(self, tag, attrs):
        self.tag = tag
        self.attrs = attrs
        if self.tag == 'link':
            self.generate_link()
        if self.tag == 'html':
            self.html_tag.append(self.getpos()[1])
    
    def handle_endtag(self, tag):
        if tag == 'html':
            self.html_tag.append(self.getpos()[1])

    def generate_link(self):
        attr_strings = []
        for attr in self.attrs:
            attr_strings.append('{0[0]}={0[1]} '.format(attr))
        string = '<%s ' % self.tag
        for attr in attr_strings:
            string += attr
        self.result.append(string+' />')

parser = UILinkParser()
index = None
html_string = None
with open("/opt/app-root/share/jupyterhub/static/jsp-ui/index.html", "r") as f:
    html_string = f.read()
    parser.feed(html_string)
    index = html_string.find('<body>')
links = parser.result
for link in links:
    html_string = html_string[:index+6]+link+html_string[index+6:]
for tag in parser.html_tag:
    html_string = html_string[:tag] + html_string[tag:]

from jupyterhub_singleuser_profiles.profiles import SingleuserProfiles

from kubespawner import KubeSpawner
class OpenShiftSpawner(KubeSpawner):
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.single_user_services = []
    self.single_user_profiles = SingleuserProfiles(gpu_mode=os.environ.get('GPU_MODE'), verify_ssl=verify_ssl)
    self.gpu_mode = self.single_user_profiles.gpu_mode
    self.gpu_count = 0
    self.deployment_size = None

  def _options_form_default(self):
    response = html_string
    return response

  def options_from_form(self, formdata):
    options = {}
    cm_data = self.single_user_profiles.get_user_profile_cm(self.user.name)
    options['custom_image'] = cm_data['last_selected_image']
    options['size'] = cm_data['last_selected_size']
    self.gpu_count = cm_data['gpu']
    self.image = options['custom_image']
    self.deployment_size = cm_data['last_selected_size']

    return options



def apply_pod_profile(spawner, pod):
  spawner.single_user_profiles.load_profiles(username=spawner.user.name)
  profile = spawner.single_user_profiles.get_merged_profile(spawner.image, user=spawner.user.name, size=spawner.deployment_size)
  return SingleuserProfiles.apply_pod_profile(spawner, pod, profile, DEFAULT_MOUNT_PATH)

def setup_environment(spawner):
    spawner.single_user_profiles.load_profiles(username=spawner.user.name)
    spawner.single_user_profiles.setup_services(spawner, spawner.image, spawner.user.name)

def clean_environment(spawner):
    spawner.single_user_profiles.clean_services(spawner, spawner.user.name)

c.JupyterHub.spawner_class = OpenShiftSpawner

c.OpenShiftSpawner.pre_spawn_hook = setup_environment
c.OpenShiftSpawner.post_stop_hook = clean_environment
c.OpenShiftSpawner.modify_pod_hook = apply_pod_profile
c.OpenShiftSpawner.cpu_limit = float(os.environ.get("SINGLEUSER_CPU_LIMIT", "1"))
c.OpenShiftSpawner.mem_limit = os.environ.get("SINGLEUSER_MEM_LIMIT", "1G")
c.OpenShiftSpawner.storage_pvc_ensure = True
c.KubeSpawner.storage_capacity = os.environ.get('SINGLEUSER_PVC_SIZE', '2Gi')
c.KubeSpawner.pvc_name_template = '%s-nb-{username}-pvc' % os.environ['JUPYTERHUB_SERVICE_NAME']
c.KubeSpawner.volumes = [dict(name='data', persistentVolumeClaim=dict(claimName=c.KubeSpawner.pvc_name_template))]
c.KubeSpawner.volume_mounts = [dict(name='data', mountPath=DEFAULT_MOUNT_PATH)]
c.KubeSpawner.user_storage_class = os.environ.get("JUPYTERHUB_STORAGE_CLASS", c.KubeSpawner.user_storage_class)
admin_users = os.environ.get('JUPYTERHUB_ADMIN_USERS')
if admin_users:
    c.Authenticator.admin_users = set(admin_users.split(','))
    