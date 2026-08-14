// 表示項目トグル (SP-03-12, DF-03-03)。ノードのどの情報を描画するかを制御する。
// サーバ側の layout.metrics.DisplayOptions とは異なり、こちらはノード寸法の
// 再計算を伴わない純粋な描画側の出し分け (Phase 4 の割り切り。10_specifications.md
// の SP-03-12 を参照)。

export interface DisplayOptions {
  showRuby: boolean;
  showBirthOrder: boolean;
  showDates: boolean;
  showPhotos: boolean;
  showFormerSurname: boolean;
}

export const DEFAULT_DISPLAY_OPTIONS: DisplayOptions = {
  showRuby: true,
  showBirthOrder: true,
  showDates: true,
  showPhotos: true,
  showFormerSurname: true,
};
