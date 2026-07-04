from locust import HttpUser, task, between

class AdminUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        pass

    @task(3)
    def get_dashboard(self):
        self.client.get('/dashboard')

    @task(2)
    def get_pending(self):
        self.client.get('/pending')

class ApiUser(HttpUser):
    wait_time = between(0.5, 2)

    @task(5)
    def send_health(self):
        self.client.get('/health')
