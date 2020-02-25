import logging

logs = ['success_log', 'error_log', 'fof_log']

for log in logs:

    logger = logging.getLogger(log)
    logger.setLevel(logging.DEBUG)
    fh = logging.FileHandler(f'./logs/{log}.log')
    fh.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    fh.setFormatter(formatter)

    logger.addHandler(fh)
