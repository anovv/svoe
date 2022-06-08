import re


class ResourceConvert:
    # https://github.com/amelbakry/kube-node-utilization/blob/master/nodeutilization.py
    def cpu(value):
        """
        Return CPU in milicores if it is configured with value
        """
        if re.match(r"[0-9]{1,9}m", str(value)):
            cpu = re.sub("[^0-9]", "", value)
        elif re.match(r"[0-9]{1,4}$", str(value)):
            cpu = int(value) * 1000
        elif re.match(r"[0-9]{1,15}n", str(value)):
            cpu = int(re.sub("[^0-9]", "", value)) // 1000000
        elif re.match(r"[0-9]{1,15}u", str(value)):
            cpu = int(re.sub("[^0-9]", "", value)) // 1000
        return int(cpu)

    def memory(value):
        """
        Return Memory in MB
        """
        if re.match(r"[0-9]{1,9}Mi?", str(value)):
            mem = re.sub("[^0-9]", "", value)
        elif re.match(r"[0-9]{1,9}Ki?", str(value)):
            mem = re.sub("[^0-9]", "", value)
            mem = int(mem) // 1024
        elif re.match(r"[0-9]{1,9}Gi?", str(value)):
            mem = re.sub("[^0-9]", "", value)
            mem = int(mem) * 1024
        return int(mem)