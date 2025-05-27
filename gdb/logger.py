import csv

class CsvLogger:
    def __init__(self, filename) -> None:
        self.filename = filename
        with open(self.filename, mode='w', newline='') as file:
            writer = csv.writer(file)
            # 写入表头
            writer.writerow(['Address/Register', 'Old Value', 'New Value'])

    def log(self, address_or_register, old_value, new_value):
        with open(self.filename, mode='a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([address_or_register, old_value, new_value])

logger = None

def init_logger(filename):
    global logger
    logger = CsvLogger(filename)

def log_single(address_or_register, old_value, new_value):
    if logger:
        logger.log(address_or_register, old_value, new_value)
    else:
        print("Injected bitflip into address/register %s: old value %s -> new value %s" % (address_or_register, old_value, new_value))
