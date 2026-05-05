import shutil
from argparse import ArgumentParser, Namespace
from pathlib import Path
from time import sleep

from aux import MyClass, my_function

import tuning

ROOT_DIR = Path(__file__).parents[1]
logger = tuning.getLogger("demo")


def basic_config(
    show_icon: bool = False,
    show_path: bool = False,
    show_time: bool = False,
    boxes: bool = False,
) -> None:
    # Configure the process root logger programmatically, like logging.basicConfig().
    tuning.basicConfig(
        level="TRACE",
        filename=".logs/usage.log",
        console=True,
        show_icon=show_icon,
        show_path=show_path,
        show_time=show_time,
        datefmt=tuning.ISO_FORMAT,
        boxes=boxes,
        force=True,
    )


def pro_config() -> None:
    # Load packaged defaults from tuning/conf.yml, then merge this override file.
    tuning.basicConfigFromYaml("examples/custom_logger.yml", force=True)


def zero_config() -> None:
    # Use default configuration, bundled with the python module
    pass


def cleanup():
    try:
        user_input = logger.prompt("INPUT nothing, just press enter")
        if user_input.strip() != "":
            logger.debug(f"Corious to DEBUG, but talking nonsense: {user_input}")
        else:
            logger.debug("Good job, you won't have to worry about DEBUG phase")
    except (EOFError, ValueError):
        pass
    sleep(1)
    shutil.rmtree(ROOT_DIR / ".logs", ignore_errors=True)
    logger.success("I can tell, it was a complete SUCCESS")
    sleep(1)


def sampling():
    levels = {
        "trace": logger.trace,
        "debug": logger.debug,
        "info": logger.info,
        "success": logger.success,
        "warning": logger.warning,
        "error": logger.error,
        "critical": logger.critical,
    }

    for lvl, lvlhandler in levels.items():
        lvlhandler(f"This is {lvl}")
        sleep(1)


def main(mode: str) -> None:
    my_function()
    try:
        if mode in ["zero", "basic"]:
            logger.warning("I WARN you, an exception is comming. Beautful, isn't it?")
        else:
            logger.warning("I WARN you, a CUSTOM LEVEL is comming. Cool, isn't it?")
        sleep(1)
        logger.my_custom_level("This is custom level")
        raise ValueError("I won't show it again, it was just an EXCEPTION")
    except (AttributeError, ValueError) as e:
        logger.exception(e)
    finally:
        sleep(1)

    _ = MyClass()
    _.action(ROOT_DIR / ".logs")

    cleanup()

    logger.trace("Keep it clear, use TRACE for your blablabla")
    sleep(1)


def _cli() -> ArgumentParser:
    parser = ArgumentParser(
        prog=Path(__file__).name,
        description="Shows some examples of how to use tuning",
    )
    parser.set_defaults(
        command="basic",
        show_icon=False,
        show_path=False,
        show_time=False,
        boxes=False,
    )
    subparsers = parser.add_subparsers(
        dest="command",
        metavar="MODE",
        help="Configuration mode",
    )

    basic_parser = subparsers.add_parser(
        "basic",
        aliases=["b"],
        help="Configure logging from source code",
    )
    basic_parser.set_defaults(command="basic")
    basic_parser.add_argument(
        "-i",
        "--icons",
        action="store_true",
        dest="show_icon",
        help="Use icons instead of symbols in console output",
    )
    basic_parser.add_argument(
        "-p",
        "--paths",
        action="store_true",
        dest="show_path",
        help="Show source paths in console output",
    )
    basic_parser.add_argument(
        "-t",
        "--times",
        action="store_true",
        dest="show_time",
        help="Show timestamps in console output",
    )
    basic_parser.add_argument(
        "-b",
        "--boxes",
        action="store_true",
        dest="boxes",
        help="Render each console log record in a styled box",
    )

    pro_parser = subparsers.add_parser(
        "pro",
        aliases=["p"],
        help="Configure logging from examples/custom_logger.yml",
    )
    pro_parser.set_defaults(command="pro")

    zero_parser = subparsers.add_parser(
        "zero",
        aliases=["z"],
        help="Use future zero-config mode",
    )
    zero_parser.set_defaults(command="zero")

    return parser


if __name__ == "__main__":
    tuning.banner()
    args: Namespace = _cli().parse_args()
    command = args.command or "basic"
    print(f"You can still print normally to the terminal (configuration mode: {command})")
    if command == "zero":
        zero_config()
    elif command == "basic":
        basic_config(
            show_icon=args.show_icon,
            show_path=args.show_path,
            show_time=args.show_time,
            boxes=args.boxes,
        )
    elif command == "pro":
        pro_config()
    main(command)
