from kivy.uix.boxlayout import BoxLayout

from app import i18n
from app.i18n import t
from app.screens.base import BaseScreen
from app.widgets import theme
from app.widgets.cards import section_title
from app.widgets.common import ALabel, AButton, AInput, Chip, Surface, rtl_row, spacer, touch
from app.widgets.icons import Icon
from app.widgets.theme import dp, fs, gap


class OnboardingScreen(BaseScreen):
    """Short first-launch welcome: language, optional name. No account, nothing sent anywhere."""

    def build(self):
        self.title_label.raw = ""
        self.header_box.height = dp(10)
        c = self.content
        c.padding = [gap(18), gap(10), gap(18), gap(24)]
        langs = [Chip(label, active=(code == i18n.language()), on_action=lambda code=code: self.pick_language(code))
                 for code, label in i18n.LANGUAGES.items()]
        c.add_widget(rtl_row(*langs, height=touch(40)))
        c.add_widget(ALabel(t("onb.title"), font_size=fs(28), bold=True))
        c.add_widget(ALabel(t("onb.subtitle"), font_size=fs(15), color=theme.MUTED))
        card = Surface(orientation="vertical", padding=gap(16), spacing=gap(12), size_hint_y=None)
        card.bind(minimum_height=card.setter("height"))
        for icon, key in (("list", "onb.point1"), ("bell", "onb.point2"), ("info", "onb.point3")):
            card.add_widget(rtl_row(Icon(icon, color=theme.ACCENT, size_dp=24),
                                    ALabel(t(key), font_size=fs(14.5)), height=dp(44), spacing=gap(12)))
        c.add_widget(card)
        c.add_widget(ALabel(t("onb.name_prompt"), font_size=fs(18), bold=True))
        self.name_input = AInput(t("onb.name_hint"), on_enter=self.start)
        c.add_widget(self.name_input)
        c.add_widget(ALabel(t("onb.name_note"), font_size=fs(12.5), color=theme.MUTED))
        self.error = ALabel("", color=theme.DANGER)
        c.add_widget(self.error)
        c.add_widget(AButton(t("onb.start"), "primary", on_action=self.start, icon="check"))
        c.add_widget(AButton(t("onb.skip"), "ghost", on_action=self.skip))

    def pick_language(self, code):
        self.app.set_preference("language", code, rebuild_to="onboarding")

    def start(self):
        self.app.finish_onboarding(self.name_input.text)

    def skip(self):
        self.app.finish_onboarding("")
