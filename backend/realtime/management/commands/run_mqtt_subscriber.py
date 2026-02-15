"""
Django management command to run MQTT subscriber.

Usage:
    python manage.py run_mqtt_subscriber

This command starts a persistent MQTT client that listens for sensor data
from TremoAI glove devices. It should be run in a separate terminal alongside
the Django development server.
"""
import logging
from django.core.management.base import BaseCommand
from realtime.mqtt_client import MQTTClient

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Django management command for running MQTT subscriber."""

    help = 'Starts MQTT subscriber for real-time glove sensor data'

    def handle(self, *args, **options):
        """Execute the command."""
        self.stdout.write(self.style.SUCCESS('Starting MQTT subscriber...'))
        self.stdout.write('Press Ctrl+C to stop')

        try:
            # Initialize and connect MQTT client
            mqtt_client = MQTTClient()
            mqtt_client.connect()  # Blocking call - runs forever

        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('\nShutting down MQTT subscriber...'))
            if mqtt_client:
                mqtt_client.disconnect()
            self.stdout.write(self.style.SUCCESS('MQTT subscriber stopped'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Fatal error: {e}'))
            logger.error(f'MQTT subscriber fatal error: {e}', exc_info=True)
            raise
