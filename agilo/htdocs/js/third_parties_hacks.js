/**
 * This file contains specific initialization hacks to support 3rd parties
 * plugins to work with Agilo UI, just work we are not responsible for 3rd
 * parties malfunctioning.
 */

$(document).ready(initThirdPartiesHacks);

function initThirdPartiesHacks() {
	initThirdParties(BASE_URL, CHROME_URL);
};


function initThirdParties(base_path, chrome_path) {
	// TracWysiwyg
	if (typeof TracWysiwyg != "undefined") {
		TracWysiwyg.getTracPaths = function() {
			return {"base": base_path, 
					"htdocs": chrome_path};
		};
	}
}
