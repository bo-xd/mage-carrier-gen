<?xml version="1.0"?>
<config xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xsi:noNamespaceSchemaLocation="urn:magento:module:Magento_Store:etc/config.xsd">
    <default>
        <carriers>
            <${carrier_code}>
                <active>0</active>
                <sallowspecific>0</sallowspecific>
                <model>${vendor}\${carrier}\Model\Carrier\${carrier}</model>
                <title>${xml_title}</title>
                <sandbox_mode>1</sandbox_mode>
                <sandbox_api_url>${xml_sandbox_url}</sandbox_api_url>
                <production_api_url>${xml_base_url}</production_api_url>
                <api_key backend_model="Magento\Config\Model\Config\Backend\Encrypted"/>
                <debug>0</debug>
                <sort_order>10</sort_order>
            </${carrier_code}>
        </carriers>
    </default>
</config>
