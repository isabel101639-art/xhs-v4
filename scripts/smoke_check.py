from app import app, init_db


def main():
    init_db()
    client = app.test_client()

    health = client.get('/healthz')
    print('healthz', health.status_code)

    home = client.get('/')
    print('home', home.status_code)

    activities = client.get('/activity')
    print('activity_list', activities.status_code)


if __name__ == '__main__':
    main()
