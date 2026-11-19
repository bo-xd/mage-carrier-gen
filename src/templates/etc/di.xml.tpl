<?xml version="1.0"?>
<config xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xsi:noNamespaceSchemaLocation="urn:magento:framework:ObjectManager/etc/config.xsd">
    <virtualType name="${vendor}\${carrier}\Logger\Handler" type="Magento\Framework\Logger\Handler\Base">
        <arguments>
            <argument name="filesystem" xsi:type="object">Magento\Framework\Filesystem\Driver\File</argument>
            <argument name="fileName" xsi:type="string">/var/log/${carrier_code}.log</argument>
        </arguments>
    </virtualType>
    <type name="${vendor}\${carrier}\Logger\Logger">
        <arguments>
            <argument name="name" xsi:type="string">${carrier_code}</argument>
            <argument name="handlers" xsi:type="array">
                <item name="system" xsi:type="object">${vendor}\${carrier}\Logger\Handler</item>
            </argument>
        </arguments>
    </type>
    <type name="${vendor}\${carrier}\Model\Carrier\${carrier}">
        <arguments>
            <argument name="logger" xsi:type="object">${vendor}\${carrier}\Logger\Logger</argument>
        </arguments>
    </type>
</config>
