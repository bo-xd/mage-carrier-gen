{
    "name": "${composer_vendor}/module-shipping-${composer_carrier}",
    "description": "${json_description}",
    "type": "magento2-module",
    "version": "${json_version}",
    "license": [
        "proprietary"
    ],
    "require": {
        "php": "~8.4.0||~8.5.0",
        "magento/framework": "^103.0",
        "magento/module-shipping": "^100.4",
        "magento/module-config": "^101.2",
        "magento/module-store": "^101.1",
        "guzzlehttp/guzzle": "^7.9",
        "psr/log": "^3.0"
    },
    "autoload": {
        "files": [
            "registration.php"
        ],
        "psr-4": {
            "${vendor}\\\\${carrier}\\\\": ""
        }
    }
}
