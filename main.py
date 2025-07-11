#!/usr/bin/env python

from watchfiles import watch
from functools import partial
import argparse
from mpv import MPV
from pathlib import Path
import sys


def main() -> None:
    # Parse command line options
    project = options()

    # Create the watcher
    watcher = Watcher(project)
    watcher.load_playlist()

    # Start watching the project path
    watchpath = project / "media" / "videos" / "main"
    if not watchpath.is_dir():
        raise NotADirectoryError(f"Watch path not a directory: {watchpath}")
    print(f"Listening to changes to {watchpath}")
    for _ in watch(watchpath):
        watcher.update_available_qualities()
        watcher.load_playlist()
        watcher.mpv.pause = False


def options():
    parser = argparse.ArgumentParser(
        description="Opens videos in MPV and watches for changes to reload MPV",
    )
    parser.add_argument(
        "--project",
        help="Manim project dir to watch (defaults to current working directory)",
        type=Path,
    )
    args = parser.parse_args()
    project: Path = args.project or Path.cwd()
    return project


class Watcher:
    def __init__(self, project: Path):
        self.project = project
        self.update_available_qualities()

        self.quality = 0
        self.show_help = False
        self.help_text = "Keybinds:"

        self.mpv = MPV(
            loop=True,
            background_color="#282828",
            osd_msg3="${?pause==yes:⏸}${!pause==yes:⏵} ${time-pos}/${duration} frame ${estimated-frame-number} of ${estimated-frame-count}",
            osd_font="monospace",
        )

        # property_observer expects an unbound function, hence partial
        self.mpv.property_observer("path")(partial(self.path_observer))

        self.keybind("q", self.close_mpv, "Close MPV")
        self.keybind(".", self.frame_step, "Frame step forward")
        self.keybind(",", self.frame_back_step, "Frame step back")
        self.keybind("SPACE", self.pause, "Pause")
        self.keybind("g-p", self.select_playlist, "Playlist select menu")
        self.keybind(">", self.playlist_next, "Playlist next")
        self.keybind("<", self.playlist_prev, "Playlist previous")
        self.keybind("'", self.cycle_quality, "Cycle through available qualities")
        self.keybind("?", self.toggle_help, "Show this help")

    def update_available_qualities(self):
        self.available_qualities = list(
            filter(
                ["480p15", "720p30", "1080p60", "1440p60", "2880p60"].__contains__,
                map(
                    lambda path: path.name,
                    (self.project / "media" / "videos" / "main").iterdir(),
                ),
            )
        )

    def path(self) -> Path:
        return (
            self.project
            / "media"
            / "videos"
            / "main"
            / self.available_qualities[self.quality]
        )

    # Looks through specified directory and adds video files to the player's playlist
    def load_playlist(self):
        path = self.path()
        if not path.is_dir():
            self.mpv.show_text(f"Cannot load playlist, path not a dir: {path}", "5000")
            print(f"Cannot load playlist, path not a dir: {path}")
            return

        if type(self.mpv.playlist_count) is int and self.mpv.playlist_count > 0:
            self.mpv.playlist_clear()
            self.mpv.playlist_remove()

        videos = sorted(
            path.glob("*.mp4"),
            key=lambda video: video.stat().st_mtime,
            reverse=True,
        )

        for video in videos:
            file = str(video.resolve())
            self.mpv.playlist_append(file)

        self.mpv.playlist_play_index(0)

    def update_overlay(self):
        invisible = "‎"
        data = f"""
            {invisible}
            {invisible}
            {self.help_text if self.show_help else ""}
            {{\\a1}} [{self.available_qualities[self.quality]}] ${{media-title}}
        """
        data = self.mpv.expand_text(data)
        self.mpv.command("osd_overlay", id="0", data=data, format="ass-events")

    def keybind(self, keydef, fn, help_text):
        self.mpv.on_key_press(keydef)(fn)
        self.help_text += f"\n{keydef:8} {help_text}"

    def close_mpv(self):
        print("Closing mpv window")
        self.mpv.stop()

    def frame_step(self):
        self.mpv.frame_step()
        self.mpv.show_progress()

    def frame_back_step(self):
        self.mpv.frame_back_step()
        self.mpv.show_progress()

    def pause(self):
        self.mpv.cycle("pause")
        self.mpv.show_progress()

    def toggle_help(self):
        self.show_help = not self.show_help
        self.update_overlay()

    def select_playlist(self):
        self.mpv.command("script-binding", "select/select-playlist")

    def playlist_next(self):
        self.mpv.playlist_next()

    def playlist_prev(self):
        self.mpv.playlist_prev()

    def cycle_quality(self):
        self.quality = (self.quality + 1) % len(self.available_qualities)
        self.mpv.show_text(f"Quality: {self.available_qualities[self.quality]}")
        self.load_playlist()

    def path_observer(self, *_):
        self.update_overlay()


if __name__ == "__main__":
    sys.exit(main())
