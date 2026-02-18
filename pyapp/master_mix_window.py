from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Callable

from PySide6.QtCore import Qt
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
    QVBoxLayout,
    QWidget,
)


@dataclass(frozen=True)
class MasterMixDefinition:
    mix_id: str
    slide_count: int
    antibodies: list[str]


def _decimal_to_fraction_text(value: float) -> str:
    if value <= 0:
        return "N/A"

    reciprocal = 1.0 / value
    rounded = round(reciprocal)
    if abs(reciprocal - rounded) < 1e-6 and rounded > 0:
        return f"1/{rounded}"

    frac = Fraction(value).limit_denominator(10000)
    return f"{frac.numerator}/{frac.denominator}"


class MasterMixWindow(QMainWindow):
    def __init__(
        self,
        mixes: list[MasterMixDefinition],
        default_concentrations: dict[str, float],
        total_slide_count: int,
        primary_volume_ul: float,
        primary_incubation_method: str,
        on_set_secondaries: Callable[[], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.mixes = mixes
        self.default_concentrations = default_concentrations
        self.total_slide_count = total_slide_count
        self.primary_volume_ul = primary_volume_ul
        self.primary_incubation_method = primary_incubation_method
        self.on_set_secondaries = on_set_secondaries

        self.spinboxes: dict[tuple[str, str], QDoubleSpinBox] = {}
        self.fraction_labels: dict[tuple[str, str], QLabel] = {}

        self._build_ui()

    def _build_ui(self) -> None:
        self.setWindowTitle("SlideApp - Master Mix Concentrations")
        self.resize(980, 860)
        self.setMinimumSize(760, 640)

        central = QWidget(self)
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(10)

        title = QLabel("Set Master Mix Concentrations", self)
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
            mix_frame = QFrame(self)
            mix_frame.setObjectName("mixFrame")
            mix_layout = QVBoxLayout(mix_frame)
            mix_layout.setContentsMargins(14, 12, 14, 12)
            mix_layout.setSpacing(8)

            heading = QLabel(f"{mix.mix_id} ({mix.slide_count} slides)", self)
            heading.setObjectName("mixHeading")
            mix_layout.addWidget(heading)

            form = QFormLayout()
            form.setHorizontalSpacing(12)
            form.setVerticalSpacing(10)

            for ab_name in mix.antibodies:
                row = QWidget(self)
                row_layout = QHBoxLayout(row)
                row_layout.setContentsMargins(0, 0, 0, 0)
                row_layout.setSpacing(8)

                spin = QDoubleSpinBox(self)
                spin.setDecimals(6)
                spin.setRange(0.0, 1.0)
                spin.setSingleStep(0.0005)
                default = self.default_concentrations.get(ab_name, 0.0)
                spin.setValue(default)

                fraction = QLabel(_decimal_to_fraction_text(default), self)
                fraction.setObjectName("fraction")

                key = (mix.mix_id, ab_name)
                self.spinboxes[key] = spin
                self.fraction_labels[key] = fraction
                spin.valueChanged.connect(
                    lambda val, mk=mix.mix_id, an=ab_name: self._on_concentration_changed(
                        mk, an, val
                    )
                )

                row_layout.addWidget(QLabel("Decimal:", self))
                row_layout.addWidget(spin)
                row_layout.addSpacing(10)
                row_layout.addWidget(QLabel("Fraction:", self))
                row_layout.addWidget(fraction)
                row_layout.addStretch()

                form.addRow(QLabel(ab_name, self), row)

            mix_layout.addLayout(form)
            body_layout.addWidget(mix_frame)

        body_layout.addStretch()
        scroll.setWidget(body)
        root.addWidget(scroll, 1)

        actions = QHBoxLayout()
        download_btn = QPushButton("Download Protocol", self)
        download_btn.clicked.connect(self._download_protocol)
        actions.addWidget(download_btn)
        actions.addStretch()
        set_secondaries_btn = QPushButton("Set Secondary Antibodies", self)
        set_secondaries_btn.clicked.connect(self._set_secondaries)
        actions.addWidget(set_secondaries_btn)
        root.addLayout(actions)

        self.setStyleSheet(
            "QMainWindow { background: #efefef; }"
            "QLabel#title { font-size: 34px; font-weight: 700; color: #111111; }"
            "QFrame#mixFrame { background: #ffffff; border-radius: 10px; }"
            "QLabel#mixHeading { font-size: 24px; font-weight: 700; color: #141414; }"
            "QLabel#fraction { color: #1c4f9a; font-weight: 600; }"
            "QLabel { font-size: 16px; color: #121212; }"
            "QDoubleSpinBox { min-width: 140px; font-size: 16px; padding: 4px 6px; }"
            "QPushButton { background: #111111; color: #f5f5f5; border: none; border-radius: 10px; padding: 10px 14px; font-size: 18px; }"
        )

    def _on_concentration_changed(self, mix_id: str, antibody_name: str, value: float) -> None:
        label = self.fraction_labels.get((mix_id, antibody_name))
        if label is not None:
            label.setText(_decimal_to_fraction_text(value))

    def _protocol_text(self) -> str:
        block_total = self.total_slide_count * 500.0
        primary_total = self.total_slide_count * self.primary_volume_ul
        pbtn_step1 = (block_total + primary_total) * 1.2

        lines: list[str] = []
        lines.append("IHC Protocol")
        lines.append("")
        lines.append("1) Prepare PBT-N")
        lines.append(
            f"- Block volume: {block_total:.1f} uL ({self.total_slide_count} slides x 500 uL)"
        )
        lines.append(
            f"- Primary solution volume: {primary_total:.1f} uL ({self.total_slide_count} slides x {self.primary_volume_ul:.1f} uL)"
        )
        lines.append(f"- Base PBT-N needed: {block_total + primary_total:.1f} uL")
        lines.append(f"- Prepare with safety factor x1.2: {pbtn_step1:.1f} uL")
        lines.append("")
        lines.append("2) Block slides")
        lines.append("- Incubate slides at RT for 1 hour.")
        lines.append("")
        lines.append("3) Prepare master mixes")
        lines.append(
            "- For each mix: antibody volume = concentration(decimal) x total mix volume."
        )
        lines.append(
            "- Then apply safety factor x1.1 to each antibody volume and to PBT-N volume."
        )
        lines.append("")

        for mix in self.mixes:
            total_mix_volume = mix.slide_count * self.primary_volume_ul
            lines.append(f"{mix.mix_id} ({mix.slide_count} slides, base total {total_mix_volume:.1f} uL)")
            ab_sum = 0.0
            for ab_name in mix.antibodies:
                spin = self.spinboxes.get((mix.mix_id, ab_name))
                conc = spin.value() if spin is not None else 0.0
                base_ab_vol = total_mix_volume * conc
                safe_ab_vol = base_ab_vol * 1.1
                ab_sum += base_ab_vol
                lines.append(
                    f"- {ab_name}: conc={conc:.6f} ({_decimal_to_fraction_text(conc)}), antibody={base_ab_vol:.3f} uL, with x1.1 -> {safe_ab_vol:.3f} uL"
                )

            base_pbtn = max(total_mix_volume - ab_sum, 0.0)
            safe_pbtn = base_pbtn * 1.1
            lines.append(
                f"- PBT-N: {base_pbtn:.3f} uL, with x1.1 -> {safe_pbtn:.3f} uL"
            )
            lines.append("")

        lines.append("4) Add master mixes to slides")
        lines.append(
            f"- Add master mix to slides and incubate using the selected method: {self.primary_incubation_method}."
        )

        return "\n".join(lines)

    def _download_protocol(self) -> None:
        default_name = "ihc_protocol.txt"
        out_path, _ = QFileDialog.getSaveFileName(
            self,
            "Download Protocol",
            str(Path.home() / "Downloads" / default_name),
            "Text Files (*.txt)",
        )
        if not out_path:
            return

        try:
            Path(out_path).write_text(self._protocol_text(), encoding="utf-8")
        except OSError as exc:
            QMessageBox.critical(self, "Save Failed", f"Could not write file:\n{exc}")
            return

        QMessageBox.information(self, "Protocol Saved", f"Saved to:\n{out_path}")

    def _set_secondaries(self) -> None:
        if self.on_set_secondaries is not None:
            self.on_set_secondaries()
