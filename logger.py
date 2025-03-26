import logging
import random

# Add sampling capability to reduce log volume in high-throughput systems
class SampledLogger(ContextLogger):
    def __init__(self, name, sample_rate=1.0, level=logging.NOTSET):
        super().__init__(name, level)
        self.sample_rate = sample_rate
        
    def _log(self, level, msg, args, exc_info=None, extra=None, stack_info=False, **kwargs):
        # Skip some logs based on sample rate (always log errors)
        if level < logging.ERROR and self.sample_rate < 1.0:
            if random.random() > self.sample_rate:
                return
                
        super()._log(level, msg, args, exc_info, extra, stack_info, **kwargs)

# Add to configure_logging function
def configure_logging(
    # ... existing parameters ...
    sample_rate=1.0,  # Add this parameter
):
    # ... existing code ...
    
    # Set the logger class based on sampling configuration
    if sample_rate < 1.0:
        logging.setLoggerClass(SampledLogger)
        logger = logging.getLogger()
        if isinstance(logger, SampledLogger):
            logger.sample_rate = sample_rate
    else:
        logging.setLoggerClass(ContextLogger)
    
    # ... rest of the function ... 