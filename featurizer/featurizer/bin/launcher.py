from featurizer.featurizer.featurizer import Featurizer

# TODO centralize this and sync with config gen scripts
FEATURIZER_CONFIG_PATH = '/etc/svoe/featurizer/configs/data-feed-config.yaml'


def main():
    fr = Featurizer(config=FEATURIZER_CONFIG_PATH)
    try:
        fr.run()
    except KeyboardInterrupt:
        pass