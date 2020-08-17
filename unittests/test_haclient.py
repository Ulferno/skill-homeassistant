from unittest import TestCase
import sys
sys.path.append('../')
for p in sys.path:
    print(p)
from ha_client import HomeAssistantClient
import unittest
from unittest import mock


kitchen_light = {'state': 'off', 'id': '1', 'dev_name': 'kitchen'}

json_data = {'attributes': {'friendly_name': 'Kitchen Lights',
                'max_mireds': 500,
                'min_mireds': 153,
                'supported_features': 151},
 'entity_id': 'light.kitchen_lights',
 'state': 'off'}

attr_resp = {
            "id": '1',
            "dev_name": {'attributes': {'friendly_name': 'Kitchen Lights', 'max_mireds': 500, 'min_mireds': 153, 'supported_features': 151}, 'entity_id': 'light.kitchen_lights', 'state': 'off'}}

headers = {
    'x-ha-access': 'password',
    'Content-Type': 'application/json'
}


class TestHaClient(TestCase):

    def test_mock_ssl(self):
        with mock.patch('requests.get') as mock_request:
            portnum = 8123
            ssl = True
            url = 'https://192.168.0.1:8123'

            mock_request.return_value.status_code = 200
            self.assertTrue(url, 'https://192.168.0.1:8123')
            self.assertTrue(portnum, 8123)
            self.assertTrue(ssl, True)
            self.assertTrue(mock_request.return_value.status_code, 200)

    def test_mock_ssl_no_port(self):
        with mock.patch('requests.get') as mock_request:
            portnum = None
            ssl = True
            url = 'https://192.168.0.1'

            mock_request.return_value.status_code = 200
            self.assertTrue(url, 'https://192.168.0.1')
            self.assertEqual(portnum, None)
            self.assertTrue(ssl, True)
            self.assertTrue(mock_request.return_value.status_code, 200)


    @mock.patch('ha_client.HomeAssistantClient.find_entity')
    def test_toggle_lights(self, mock_get):
        ha = HomeAssistantClient(host='192.168.0.1', token='token', portnum=8123, ssl=True)
        ha.find_entity = mock.MagicMock()
        entity = ha.find_entity(kitchen_light['dev_name'], 'light')
        mock_get.entity = {
                "id": '1',
                "dev_name": {'attributes': {'friendly_name': 'Kitchen Lights', 'max_mireds': 500, 'min_mireds': 153, 'supported_features': 151}, 'entity_id': 'light.kitchen_lights', 'state': 'off'}}
        self.assertEqual(mock_get.entity, attr_resp)
        ha_data = {'entity_id': entity['id']}
        state = entity['state']
        if state == 'on':
            ha.execute_service = mock.MagicMock()
            r = ha.execute_service("homeassistant", "turn_off",
                                   ha_data)
            if r.status_code == 200:
                entity = ha.find_entity(kitchen_light['dev_name'], 'light')
                if entity['state'] == 'off':
                    self.assertTrue(True)
                if entity['best_score'] >= 50:
                    self.assertTrue(True)

        else:
            ha.execute_service = mock.MagicMock()
            r = ha.execute_service("homeassistant", "turn_on",
                                   ha_data)
            if r.status_code == 200:
                if entity['state'] == 'on':
                    self.assertTrue(True)


if __name__ == '__main__':
    unittest.main()



