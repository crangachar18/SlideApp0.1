from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from PySide6.QtWidgets import (
    QFileDialog,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


def _fraction_to_decimal(value: str) -> float:
    token = value.strip()
    if not token:
        return 0.0
    if "/" in token:
        num_s, den_s = token.split("/", 1)
        try:
            num = float(num_s.strip())
            den = float(den_s.strip())
            if den == 0:
                return 0.0
            return num / den
        except ValueError:
            return 0.0
    try:
        return float(token)
    except ValueError:
        return 0.0


def _decimal_to_fraction_text(value: float) -> str:
    if value <= 0:
        return "N/A"
    denom = round(1.0 / value)
    if denom > 0 and abs(value - (1.0 / denom)) < 1e-6:
        return f"1/{denom}"
    return f"{value:.6f}"


@dataclass(frozen=True)
class SecondaryMixEntry:
    mix_id: str
    slide_count: int
    channel_to_secondary: dict[str, str]
    channel_to_fraction: dict[str, str]


class SecondaryMasterMixWindow(QMainWindow):
    def __init__(
        self,
        mixes: list[SecondaryMixEntry],
        total_slide_count: int,
        secondary_volume_ul: float,
        secondary_incubation_method: str,
        edu_enabled: bool,
        on_continue: Callable[[], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.mixes = mixes
        self.total_slide_count = total_slide_count
        self.secondary_volume_ul = secondary_volume_ul
        self.secondary_incubation_method = secondary_incubation_method
        self.edu_enabled = edu_enabled
        self.on_continue = on_continue

        self.spinboxes: dict[tuple[str, str], QDoubleSpinBox] = {}
        self.protocol_preview: QTextEdit | None = None

        self._build_ui()
        self._refresh_protocol_preview()

    def _build_ui(self) -> None:
        self.setWindowTitle("SlideApp - Secondary Master Mix Construction")
        self.resize(1080, 900)
        self.setMinimumSize(860, 680)

        central = QWidget(self)
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(10)

        title = QLabel("Secondary Master Mix Construction", self)
        title.setObjectName("title")
        root.addWidget(title)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        body = QWidget(self)
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(14)

        for mix in self.mixes:
            frame = QFrame(self)
            frame.setObjectName("mixFrame")
            frame_layout = QVBoxLayout(frame)
            frame_layout.setContentsMargins(14, 12, 14, 12)
            frame_layout.setSpacing(8)

            heading = QLabel(f"{mix.mix_id} ({mix.slide_count} slides)", self)
            heading.setObjectName("mixHeading")
            frame_layout.addWidget(heading)

            total_mix = mix.slide_count * self.secondary_volume_ul * 1.2
            frame_layout.addWidget(
                QLabel(
                    f"Total mix volume = {mix.slide_count} x {self.secondary_volume_ul:.1f} uL x 1.2 = {total_mix:.1f} uL",
                    self,
                )
            )

            form = QFormLayout()
            form.setHorizontalSpacing(12)
            form.setVerticalSpacing(8)

            for channel in ["A488", "Cy3", "A647"]:
                sec_name = mix.channel_to_secondary.get(channel, "")
                if not sec_name:
                    continue
                fraction = mix.channel_to_fraction.get(channel, "")
                default_decimal = _fraction_to_decimal(fraction)

                row = QWidget(self)
                row_layout = QHBoxLayout(row)
                row_layout.setContentsMargins(0, 0, 0, 0)
                row_layout.setSpacing(8)

                spin = QDoubleSpinBox(self)
                spin.setDecimals(6)
                spin.setRange(0.0, 1.0)
                spin.setSingleStep(0.0005)
                spin.setValue(default_decimal)
                spin.valueChanged.connect(self._refresh_protocol_preview)

                frac_label = QLabel(_decimal_to_fraction_text(default_decimal), self)

                key = (mix.mix_id, channel)
                self.spinboxes[key] = spin
                spin.valueChanged.connect(
                    lambda v, label=frac_label: label.setText(_decimal_to_fraction_text(v))
                )

                row_layout.addWidget(QLabel("Decimal:", self))
                row_layout.addWidget(spin)
                row_layout.addSpacing(8)
                row_layout.addWidget(QLabel("Fraction:", self))
                row_layout.addWidget(frac_label)
                row_layout.addStretch()

                form.addRow(QLabel(f"{channel}: {sec_name}", self), row)

            frame_layout.addLayout(form)
            body_layout.addWidget(frame)

        body_layout.addStretch()
        scroll.setWidget(body)
        root.addWidget(scroll, 1)

        self.protocol_preview = QTextEdit(self)
        self.protocol_preview.setReadOnly(True)
        self.protocol_preview.setMinimumHeight(220)
        root.addWidget(self.protocol_preview)

        actions = QHBoxLayout()
        download = QPushButton("Download Protocol", self)
        download.clicked.connect(self._download_protocol)
        actions.addWidget(download)
        actions.addStretch()

        continue_label = "Continue to EdU" if self.edu_enabled else "Confirm Slide Book"
        continue_btn = QPushButton(continue_label, self)
        continue_btn.clicked.connect(self._continue)
        actions.addWidget(continue_btn)
        root.addLayout(actions)

        self.setStyleSheet(
            "QMainWindow { background: #efefef; }"
            "QLabel#title { font-size: 34px; font-weight: 700; color: #111111; }"
            "QFrame#mixFrame { background: #ffffff; border-radius: 10px; }"
            "QLabel#mixHeading { font-size: 24px; font-weight: 700; color: #141414; }"
            "QLabel { font-size: 16px; color: #121212; }"
            "QDoubleSpinBox { min-width: 140px; font-size: 16px; padding: 4px 6px; }"
            "QTextEdit { background: #ffffff; color: #111111; font-size: 14px; }"
            "QPushButton { background: #111111; color: #f5f5f5; border: none; border-radius: 10px; padding: 10px 14px; font-size: 18px; }"
        )

    def _protocol_text(self) -> str:
        block_total = self.total_slide_count * 500.0
        block_safe = block_total * 1.2

        lines: list[str] = []
        lines.append("Secondary IHC Protocol")
        lines.append("")
        lines.append("1) Block all slides in PBT-N")
        lines.append(
            f"- Base PBT-N block volume: {self.total_slide_count} slides x 500 uL = {block_total:.1f} uL"
        )
        lines.append(f"- Prepare with safety factor x1.2: {block_safe:.1f} uL")
        lines.append("- Incubate for 30 min to 1 hr.")
        lines.append("")
        lines.append("2) Prepare secondary master mixes")

        for mix in self.mixes:
            total_mix = mix.slide_count * self.secondary_volume_ul * 1.2
            lines.append(f"{mix.mix_id} ({mix.slide_count} slides)")
            lines.append(
                f"- Total mix volume: {mix.slide_count} x {self.secondary_volume_ul:.1f} uL x 1.2 = {total_mix:.1f} uL"
            )

            sec_sum = 0.0
            for channel in ["A488", "Cy3", "A647"]:
                sec_name = mix.channel_to_secondary.get(channel, "")
                if not sec_name:
                    continue
                spin = self.spinboxes.get((mix.mix_id, channel))
                dec = spin.value() if spin is not None else _fraction_to_decimal(
                    mix.channel_to_fraction.get(channel, "")
                )
                vol = total_mix * dec
                sec_sum += vol
                lines.append(
                    f"- {channel} ({sec_name}): {dec:.6f} ({_decimal_to_fraction_text(dec)}) -> {vol:.3f} uL"
                )

            pbt_vol = max(total_mix - sec_sum, 0.0)
            lines.append(f"- Add PBT first: {pbt_vol:.3f} uL")
            lines.append("- Then add secondaries in order: A488, Cy3, A647.")
            lines.append("")

        lines.append("3) Add secondary mixes to slides")
        lines.append(f"- Incubate using preset method: {self.secondary_incubation_method}.")

        return "\n".join(lines)

    def _refresh_protocol_preview(self) -> None:
        if self.protocol_preview is not None:
            self.protocol_preview.setPlainText(self._protocol_text())

    def _download_protocol(self) -> None:
        out_path, _ = QFileDialog.getSaveFileName(
            self,
            "Download Protocol",
            str(Path.home() / "Downloads" / "secondary_protocol.txt"),
            "Text Files (*.txt)",
        )
        if not out_path:
            return

        text = self._protocol_text()
        try:
            Path(out_path).write_text(text, encoding="utf-8")
        except OSError as exc:
            QMessageBox.critical(self, "Save Failed", f"Could not write file:\n{exc}")
            return

        QMessageBox.information(self, "Protocol Saved", f"Saved to:\n{out_path}")

    def _continue(self) -> None:
        if self.on_continue is not None:
            self.on_continue()
