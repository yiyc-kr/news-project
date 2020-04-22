import argparse
import toml
import datetime


def get_article_id(url, params):
    params['date'] = params['date'].strftime("%Y%m%d")
    return 0;


def main():
    parser = argparse.ArgumentParser()

    # Config file parameters
    parser.add_argument('--config_file', '-c', type=str, default=None)

    args = parser.parse_args()

    if args.config_file:
        config = toml.load(args.config_file)
        for key_ in config:
            setattr(args, key_, config[key_])

    url = args.url
    dates = args.dates
    params = args.parameters

    for days_ in range(dates):
        print(params)
        params['date'] = params['date'] - datetime.timedelta(days=days_)
        print(params)

    print(args.parameters['date'] - datetime.timedelta(days=1))


if __name__ == "__main__":
    main()