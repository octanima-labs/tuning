from tunning import TunnedLogger


logger = TunnedLogger.from_yaml(
    "examples/custom_logger.yml",
    name="demo",
    force=True,
)

logger.trace("loading configuration")
logger.info("application started")
logger.success("everything looks good")
logger.my_custom_level("This is my custom level")

name = logger.prompt("Your name?")
logger.info("hello %s", name)
