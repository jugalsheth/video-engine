import {loadFont as loadBebas} from '@remotion/google-fonts/BebasNeue';
import {loadFont as loadInter} from '@remotion/google-fonts/Inter';

const bebas = loadBebas();
const inter = loadInter();

export const FONT_HEADLINE = bebas.fontFamily;
export const FONT_BODY = inter.fontFamily;
