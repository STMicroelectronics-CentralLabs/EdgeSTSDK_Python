################################################################################
# COPYRIGHT(c) 2018 STMicroelectronics                                         #
#                                                                              #
# Redistribution and use in source and binary forms, with or without           #
# modification, are permitted provided that the following conditions are met:  #
#   1. Redistributions of source code must retain the above copyright notice,  #
#      this list of conditions and the following disclaimer.                   #
#   2. Redistributions in binary form must reproduce the above copyright       #
#      notice, this list of conditions and the following disclaimer in the     #
#      documentation and/or other materials provided with the distribution.    #
#   3. Neither the name of STMicroelectronics nor the names of its             #
#      contributors may be used to endorse or promote products derived from    #
#      this software without specific prior written permission.                #
#                                                                              #
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"  #
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE    #
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE   #
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE    #
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR          #
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF         #
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS     #
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN      #
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)      #
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE   #
# POSSIBILITY OF SUCH DAMAGE.                                                  #
################################################################################


"""azure_client

The azure_client module represents a client capable of connecting to the Microsoft
IoT Hub and performing edge operations through the azure-iot-sdk (python).
"""


# IMPORT

import sys

import iothub_client
# pylint: disable=E0611
from iothub_client import IoTHubClient, IoTHubModuleClient, IoTHubClientError, IoTHubTransportProvider
from iothub_client import IoTHubMessage, IoTHubMessageDispositionResult, IoTHubError, DeviceMethodReturnValue

from edge_st_sdk.edge_client import EdgeClient
from edge_st_sdk.utils.edge_st_exceptions import WrongInstantiationException
from edge_st_sdk.azure.azure_utils import ReceiveContext
from enum import Enum

# CLASSES

class AzureEdgeProtocol(Enum):
    HTTP = 0
    AMQP = 1
    MQTT = 2

class AzureClient(EdgeClient):
    """Class responsible for handling an Azure Edge Module client used for MQTT/AMQP
    communication (Protocol Translation) with Azure IoT Hub"""

    _TIMEOUT_s = 10000
    """Timeout for messages"""
    _subscribe_callback = None

    def __init__(self, module_name, connection_string=None, root_ca_cert=None, protocol=IoTHubTransportProvider.MQTT):
        self.module_name = module_name
        self.client_protocol = protocol
        self.connection_string = connection_string
        self.root_ca_cert = root_ca_cert
        if self.connection_string is None:
            self.client = IoTHubModuleClient()
        else:
            self.client = IoTHubClient(self.connection_string, self.client_protocol)
        self._connected = False

    def get_name(self):
        return self.module_name

    def connect(self):        
        if self.connection_string is None:
            # not really a "connect"
            self.client.create_from_environment(self.client_protocol)
        else:
            if len(self.root_ca_cert) > 0:
                cert_data = ''
                with open(self.root_ca_cert, 'rb') as cert_file:
                    cert_data = cert_file.read()
                try:
                    self.client.set_option("TrustedCerts", cert_data)
                except IoTHubClientError as iothub_client_error:
                    return False
        # set the time until a message times out
        self.client.set_option("messageTimeout", self._TIMEOUT_s)
        self._connected = True
        return True

    def disconnect(self):
        # not supported
        self._connected = False

    def publish(self, msg, send_confirmation_callback, topic=None, send_context=None):
        if self._connected:
            event = IoTHubMessage(bytearray(msg, 'utf8'))
            self.client.send_event_async(topic, event, send_confirmation_callback, send_context) \
                if self.connection_string is None \
                else self.client.send_event_async(event, send_confirmation_callback, send_context)

    def subscribe(self, callback, topic=None, user_context=None):
        if self._connected:
            self.client.set_message_callback(topic, self._subscribe_callback, ReceiveContext(callback, user_context)) \
                if self.connection_string is None \
                else self.client.set_message_callback(self._subscribe_callback, ReceiveContext(callback, 0))

    def unsubscribe(self, topic):
        # not supported
        # set topic subsciption to null?
        return

    # Send Twin reported properties
    def update_shadow_state(self, payload, callback, context):
        if self._connected:
            self.client.send_reported_state(payload, len(payload), callback, context)

    def get_shadow_state(self, callback, timeout_s):
        # not supported
        # get twin desired properties is however supported from the device services side (backend application)
        return

    def delete_shadow_state(self, callback, timeout_s):
        # not supported
        return

    # Sets the callback when a module twin's desired properties are updated.
    def set_twin_callback(self, twin_callback, user_context):
        if self._connected:
            self.client.set_module_twin_callback(twin_callback, user_context) \
                if self.connection_string is None \
                else self.client.set_device_twin_callback(twin_callback, user_context)

    # Register a callback for module method
    def set_method_callback(self, method_callback, user_context):
        if self._connected:
            self.client.set_module_method_callback(method_callback, user_context) \
                if self.connection_string is None \
                else self.client.set_device_method_callback(method_callback, user_context)

    def _subscribe_callback(self, message, context):
        callback = context._get_callback()
        # print('\n_subscribe_calback')
        callback(message, context._get_context())
        return IoTHubMessageDispositionResult.ACCEPTED

