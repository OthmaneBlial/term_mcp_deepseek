import psutil
import os

class ProcessTracker:
    """
    A rough approximation of the 'ProcessTracker' logic. We track the
    CPU usage for the current Python process and its children, 
    to see if the system is 'idle'.
    """

    def get_active_process(self):
        """
        Returns a dict containing the total CPU usage of this 
        process + its children as an approximation.
        """
        parent = psutil.Process(os.getpid())
        children = parent.children(recursive=True)

        total_cpu = 0.0
        breakdown = []

        # get parent's CPU usage
        parent_cpu = parent.cpu_percent(interval=0.0)
        total_cpu += parent_cpu
        breakdown.append({
            "name": parent.name(),
            "pid": str(parent.pid),
            "cpuPercent": parent_cpu,
            "memory": str(parent.memory_info().rss)
        })

        # sum children's CPU usage
        for c in children:
            with c.oneshot():
                c_cpu = c.cpu_percent(interval=0.0)
                total_cpu += c_cpu
                breakdown.append({
                    "name": c.name(),
                    "pid": str(c.pid),
                    "cpuPercent": c_cpu,
                    "memory": str(c.memory_info().rss)
                })

        return {
            "metrics": {
                "totalCPUPercent": total_cpu,
                "totalMemoryMB": 0,  # not used here
                "processBreakdown": breakdown
            }
        }
