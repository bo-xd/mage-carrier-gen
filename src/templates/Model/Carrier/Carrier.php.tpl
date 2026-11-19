<?php

declare(strict_types=1);

namespace ${vendor}\${carrier}\Model\Carrier;

use GuzzleHttp\ClientFactory;
use GuzzleHttp\Exception\GuzzleException;
use Magento\CatalogInventory\Api\StockRegistryInterface;
use Magento\Directory\Helper\Data as DirectoryData;
use Magento\Directory\Model\CountryFactory;
use Magento\Directory\Model\CurrencyFactory;
use Magento\Directory\Model\RegionFactory;
use Magento\Framework\App\CacheInterface;
use Magento\Framework\App\Config\ScopeConfigInterface;
use Magento\Framework\DataObject;
use Magento\Framework\Encryption\EncryptorInterface;
use Magento\Framework\Xml\Security;
use Magento\Quote\Model\Quote\Address\RateRequest;
use Magento\Quote\Model\Quote\Address\RateResult\ErrorFactory;
use Magento\Quote\Model\Quote\Address\RateResult\Method;
use Magento\Quote\Model\Quote\Address\RateResult\MethodFactory;
use Magento\Shipping\Model\Carrier\AbstractCarrierOnline;
use Magento\Shipping\Model\Carrier\CarrierInterface;
use Magento\Shipping\Model\Rate\Result;
use Magento\Shipping\Model\Rate\ResultFactory;
use Magento\Shipping\Model\Tracking\Result as TrackResult;
use Magento\Shipping\Model\Tracking\Result\ErrorFactory as TrackErrorFactory;
use Magento\Shipping\Model\Tracking\Result\Status;
use Magento\Shipping\Model\Tracking\Result\StatusFactory as TrackStatusFactory;
use Magento\Shipping\Model\Tracking\ResultFactory as TrackResultFactory;
use Magento\Shipping\Model\Simplexml\ElementFactory;
use Psr\Log\LoggerInterface;

class ${carrier} extends AbstractCarrierOnline implements CarrierInterface
{
    private const int CACHE_TTL_SECONDS = 300;
    private const float CONNECT_TIMEOUT_SECONDS = 5.0;
    private const float REQUEST_TIMEOUT_SECONDS = 10.0;

    private const string AUTH_SCHEME = '${auth_scheme}';
    private const string AUTH_HEADER = '${auth_header}';
    private const string AUTH_QUERY_PARAM = '${auth_query_param}';
    private const string AUTH_PREFIX = '${auth_prefix}';

    private const string RATE_METHOD = '${rate_method}';
    private const string RATE_PATH = '${rate_path}';
    private const array RATE_REQUEST_MAPPING = ${rate_request_mapping_php};
    private const array RATE_RESPONSE_MAPPING = ${rate_response_mapping_php};

    private const string SHIPMENT_METHOD = '${shipment_method}';
    private const string SHIPMENT_PATH = '${shipment_path}';
    private const array SHIPMENT_REQUEST_MAPPING = ${shipment_request_mapping_php};
    private const array SHIPMENT_RESPONSE_MAPPING = ${shipment_response_mapping_php};

    private const string TRACKING_METHOD = '${tracking_method}';
    private const string TRACKING_PATH = '${tracking_path}';
    private const array TRACKING_RESPONSE_MAPPING = ${tracking_response_mapping_php};

    /**
     * @var string
     */
    protected $$_code = '${carrier_code}';

    /**
     * @var bool
     */
    protected $$_isFixed = false;

    public function __construct(
        ScopeConfigInterface $$scopeConfig,
        ErrorFactory $$rateErrorFactory,
        LoggerInterface $$logger,
        Security $$xmlSecurity,
        ElementFactory $$xmlElFactory,
        ResultFactory $$rateFactory,
        MethodFactory $$rateMethodFactory,
        TrackResultFactory $$trackFactory,
        TrackErrorFactory $$trackErrorFactory,
        TrackStatusFactory $$trackStatusFactory,
        RegionFactory $$regionFactory,
        CountryFactory $$countryFactory,
        CurrencyFactory $$currencyFactory,
        DirectoryData $$directoryData,
        StockRegistryInterface $$stockRegistry,
        private readonly EncryptorInterface $$encryptor,
        private readonly CacheInterface $$cache,
        private readonly ClientFactory $$httpClientFactory,
        array $$data = []
    ) {
        parent::__construct(
            $$scopeConfig,
            $$rateErrorFactory,
            $$logger,
            $$xmlSecurity,
            $$xmlElFactory,
            $$rateFactory,
            $$rateMethodFactory,
            $$trackFactory,
            $$trackErrorFactory,
            $$trackStatusFactory,
            $$regionFactory,
            $$countryFactory,
            $$currencyFactory,
            $$directoryData,
            $$stockRegistry,
            $$data
        );
    }

    public function collectRates(RateRequest $$request): Result|bool
    {
        if (!$$this->getConfigFlag('active') || self::RATE_PATH === '') {
            return false;
        }

        $$payload = $$this->mapFields(
            [
                'dest_postcode' => (string) $$request->getDestPostcode(),
                'dest_country_id' => (string) $$request->getDestCountryId(),
                'package_weight' => (float) $$request->getPackageWeight(),
                'origin_postcode' => (string) $$request->getPostcode(),
                'origin_country_id' => (string) $$request->getCountryId(),
            ],
            self::RATE_REQUEST_MAPPING
        );

        $$cacheKey = sprintf(
            '%s_rates_%s',
            $$this->_code,
            hash('sha256', (string) json_encode($$payload))
        );

        $$cached = $$this->cache->load($$cacheKey);
        if (is_string($$cached) && $$cached !== '') {
            $$decoded = json_decode($$cached, true);
            if (is_array($$decoded)) {
                return $$this->buildRateResult($$decoded);
            }
        }

        try {
            $$responseData = $$this->sendApiRequest(self::RATE_METHOD, self::RATE_PATH, $$payload);
            if ($$responseData === null) {
                return false;
            }

            $$this->cache->save(
                (string) json_encode($$responseData),
                $$cacheKey,
                [$$this->_code . '_rates'],
                self::CACHE_TTL_SECONDS
            );

            return $$this->buildRateResult($$responseData);
        } catch (\Throwable $$e) {
            $$this->logDebug('Rate collection failed: ' . $$e->getMessage(), true);
            return false;
        }
    }

    public function requestToShipment(DataObject $$request): DataObject
    {
        return parent::requestToShipment($$request);
    }

    protected function _doShipmentRequest(DataObject $$request): DataObject
    {
        $$result = new DataObject();

        if (self::SHIPMENT_PATH === '') {
            $$result->setErrors(__('Shipment endpoint is not configured for %1.', $$this->_code));
            return $$result;
        }

        $$orderShipment = $$request->getOrderShipment();
        $$order = $$orderShipment ? $$orderShipment->getOrder() : null;

        $$payload = $$this->mapFields(
            [
                'dest_postcode' => (string) $$request->getRecipientAddressPostalCode(),
                'dest_country_id' => (string) $$request->getRecipientAddressCountryCode(),
                'package_weight' => (float) $$request->getPackageWeight(),
                'order_increment_id' => $$order ? (string) $$order->getIncrementId() : '',
                'origin_postcode' => (string) $$request->getShipperAddressPostalCode(),
                'origin_country_id' => (string) $$request->getShipperAddressCountryCode(),
            ],
            self::SHIPMENT_REQUEST_MAPPING
        );

        try {
            $$responseData = $$this->sendApiRequest(self::SHIPMENT_METHOD, self::SHIPMENT_PATH, $$payload);
            if ($$responseData === null) {
                $$result->setErrors(__('Empty response from shipment API.'));
                return $$result;
            }

            $$trackingKey = self::SHIPMENT_RESPONSE_MAPPING['tracking_number'] ?? 'tracking_number';
            $$labelKey = self::SHIPMENT_RESPONSE_MAPPING['shipping_label'] ?? 'shipping_label';

            $$trackingNumber = (string) ($$this->extractPath($$responseData, $$trackingKey) ?? '');
            $$rawLabel = (string) ($$this->extractPath($$responseData, $$labelKey) ?? '');

            $$decodedLabel = base64_decode($$rawLabel, true);
            $$labelContent = $$decodedLabel !== false ? $$decodedLabel : $$rawLabel;

            $$result->setTrackingNumber($$trackingNumber);
            $$result->setShippingLabelContent($$labelContent);
            $$result->setInfo([
                [
                    'tracking_number' => $$trackingNumber,
                    'label_content' => $$labelContent,
                ],
            ]);
        } catch (\Throwable $$e) {
            $$this->logDebug('Shipment creation failed: ' . $$e->getMessage(), true);
            $$result->setErrors($$e->getMessage());
        }

        return $$result;
    }

    public function getTrackingInfo($$trackingNumber): Status|TrackResult|bool
    {
        $$trackingCode = trim((string) $$trackingNumber);
        if ($$trackingCode === '' || self::TRACKING_PATH === '') {
            return false;
        }

        $$path = str_replace(
            ['{tracking_number}', '{trackingNumber}', '{id}'],
            rawurlencode($$trackingCode),
            self::TRACKING_PATH
        );

        $$query = $$path === self::TRACKING_PATH ? ['tracking_number' => $$trackingCode] : [];

        try {
            $$responseData = $$this->sendApiRequest(self::TRACKING_METHOD, $$path, $$query);
            if ($$responseData === null) {
                return false;
            }

            $$statusKey = self::TRACKING_RESPONSE_MAPPING['status'] ?? 'status';
            $$eventsKey = self::TRACKING_RESPONSE_MAPPING['events'] ?? 'events';

            /** @var Status $$trackingStatus */
            $$trackingStatus = $$this->_trackStatusFactory->create();
            $$trackingStatus->setCarrier($$this->_code);
            $$trackingStatus->setCarrierTitle($$this->getCarrierTitle());
            $$trackingStatus->setTracking($$trackingCode);
            $$trackingStatus->setStatus((string) ($$this->extractPath($$responseData, $$statusKey) ?? 'Unknown'));

            $$events = $$this->extractPath($$responseData, $$eventsKey);
            if (is_array($$events)) {
                $$trackingStatus->setProgressdetail($$events);
            }

            return $$trackingStatus;
        } catch (\Throwable $$e) {
            $$this->logDebug('Tracking lookup failed: ' . $$e->getMessage(), true);
            return false;
        }
    }

    /**
     * @return array<string, string>
     */
    public function getAllowedMethods(): array
    {
        return [$$this->_code => $$this->getCarrierTitle()];
    }

    private function getCarrierTitle(): string
    {
        $$title = (string) $$this->getConfigData('title');
        return $$title !== '' ? $$title : '${php_title}';
    }

    private function getApiBaseUrl(): string
    {
        $$isSandbox = $$this->getConfigFlag('sandbox_mode');
        $$url = $$isSandbox
            ? (string) $$this->getConfigData('sandbox_api_url')
            : (string) $$this->getConfigData('production_api_url');

        return rtrim($$url, '/');
    }

    private function getDecryptedApiKey(): string
    {
        $$raw = (string) $$this->getConfigData('api_key');
        if ($$raw === '') {
            return '';
        }

        return (string) $$this->encryptor->decrypt($$raw);
    }

    /**
     * @param array<string, mixed> $$payload
     * @return array<string, mixed>|null
     * @throws GuzzleException
     */
    private function sendApiRequest(string $$method, string $$path, array $$payload): ?array
    {
        $$baseUrl = $$this->getApiBaseUrl();
        if ($$baseUrl === '') {
            return null;
        }

        $$headers = ['Accept' => 'application/json'];
        $$query = [];
        $$apiKey = $$this->getDecryptedApiKey();

        if ($$apiKey !== '') {
            if (self::AUTH_SCHEME === 'bearer') {
                $$headers['Authorization'] = 'Bearer ' . $$apiKey;
            } elseif (self::AUTH_SCHEME === 'api_key_header' && self::AUTH_HEADER !== '') {
                $$prefix = self::AUTH_PREFIX !== '' ? self::AUTH_PREFIX . ' ' : '';
                $$headers[self::AUTH_HEADER] = $$prefix . $$apiKey;
            } elseif (self::AUTH_SCHEME === 'api_key_query' && self::AUTH_QUERY_PARAM !== '') {
                $$query[self::AUTH_QUERY_PARAM] = $$apiKey;
            } elseif (self::AUTH_SCHEME === 'basic') {
                $$headers['Authorization'] = 'Basic ' . base64_encode($$apiKey);
            }
        }

        $$upperMethod = strtoupper($$method);
        $$options = [
            'headers' => $$headers,
            'connect_timeout' => self::CONNECT_TIMEOUT_SECONDS,
            'timeout' => self::REQUEST_TIMEOUT_SECONDS,
        ];

        if ($$upperMethod === 'GET') {
            $$options['query'] = array_merge($$query, $$payload);
        } else {
            if ($$query !== []) {
                $$options['query'] = $$query;
            }
            $$options['json'] = $$payload;
        }

        $$client = $$this->httpClientFactory->create(['config' => ['base_uri' => $$baseUrl . '/']]);
        $$relativePath = ltrim($$path, '/');

        $$this->logDebug(sprintf('API Request %s %s/%s', $$upperMethod, $$baseUrl, $$relativePath));
        $$response = $$client->request($$upperMethod, $$relativePath, $$options);
        $$body = (string) $$response->getBody();
        $$this->logDebug('API Response: ' . $$body);

        $$decoded = json_decode($$body, true);
        return is_array($$decoded) ? $$decoded : null;
    }

    /**
     * @param array<string, mixed> $$responseData
     */
    private function buildRateResult(array $$responseData): Result
    {
        /** @var Result $$result */
        $$result = $$this->_rateFactory->create();

        $$ratesListKey = self::RATE_RESPONSE_MAPPING['rates_list'] ?? 'rates';
        $$methodCodeKey = self::RATE_RESPONSE_MAPPING['method_code'] ?? 'method_code';
        $$methodTitleKey = self::RATE_RESPONSE_MAPPING['method_title'] ?? 'method_title';
        $$priceKey = self::RATE_RESPONSE_MAPPING['price'] ?? 'price';
        $$carrierTitleKey = self::RATE_RESPONSE_MAPPING['carrier_title'] ?? 'carrier_title';

        $$rawRates = $$this->extractPath($$responseData, $$ratesListKey);
        $$rateItems = is_array($$rawRates) && array_is_list($$rawRates)
            ? $$rawRates
            : [$$responseData];

        foreach ($$rateItems as $$index => $$item) {
            if (!is_array($$item)) {
                continue;
            }

            $$price = $$this->extractPath($$item, $$priceKey);
            if ($$price === null || !is_numeric($$price)) {
                continue;
            }

            /** @var Method $$method */
            $$method = $$this->_rateMethodFactory->create();
            $$method->setCarrier($$this->_code);
            $$method->setCarrierTitle((string) ($$this->extractPath($$item, $$carrierTitleKey) ?? $$this->getCarrierTitle()));
            $$method->setMethod((string) ($$this->extractPath($$item, $$methodCodeKey) ?? 'standard_' . $$index));
            $$method->setMethodTitle((string) ($$this->extractPath($$item, $$methodTitleKey) ?? $$this->getCarrierTitle()));
            $$method->setPrice((float) $$price);
            $$method->setCost((float) $$price);

            $$result->append($$method);
        }

        return $$result;
    }

    /**
     * @param array<string, mixed> $$source
     * @param array<string, string> $$mapping
     * @return array<string, mixed>
     */
    private function mapFields(array $$source, array $$mapping): array
    {
        $$mapped = [];
        foreach ($$source as $$key => $$value) {
            $$targetKey = $$mapping[$$key] ?? $$key;
            $$mapped[$$targetKey] = $$value;
        }
        return $$mapped;
    }

    /**
     * @param array<string, mixed> $$data
     */
    private function extractPath(array $$data, string $$path): mixed
    {
        if ($$path === '') {
            return null;
        }

        if (array_key_exists($$path, $$data)) {
            return $$data[$$path];
        }

        $$current = $$data;
        foreach (explode('.', $$path) as $$segment) {
            if (!is_array($$current) || !array_key_exists($$segment, $$current)) {
                return null;
            }
            $$current = $$current[$$segment];
        }

        return $$current;
    }

    private function logDebug(string $$message, bool $$isError = false): void
    {
        if ($$isError) {
            $$this->_logger->error($$message);
            return;
        }

        if ($$this->getConfigFlag('debug')) {
            $$this->_logger->debug($$message);
        }
    }
}
