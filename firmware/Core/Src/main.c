/* USER CODE BEGIN Header */
/**
 ******************************************************************************
 * @file           : main.c
 * @brief          : Main program body
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2026 STMicroelectronics.
 * All rights reserved.
 *
 * This software is licensed under terms that can be found in the LICENSE file
 * in the root directory of this software component.
 * If no LICENSE file comes with this software, it is provided AS-IS.
 *
 ******************************************************************************
 */
/* USER CODE END Header */
/* Includes ------------------------------------------------------------------*/
#include "main.h"

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */
#include "samples.h"
/* USER CODE END Includes */

/* Private typedef -----------------------------------------------------------*/
/* USER CODE BEGIN PTD */

/* USER CODE END PTD */

/* Private define ------------------------------------------------------------*/
/* USER CODE BEGIN PD */
#define RAW_DATA_SIZE 1600
#define OVR 32
#define P 5
#define DATA_SIZE (RAW_DATA_SIZE / OVR)
#define UART_TX_BUF_SIZE (DATA_SIZE * 2)  // batch size
#define UART_RX_BUF_SIZE 4
#define SAMPLES_PER_SECOND 10000
#define DAC_LUT_SIZE 1000

//typedef struct __attribute__((packed)) {
//	uint32_t sync;
//	uint8_t data[UART_TX_BUF_SIZE];
//} UartPacket;
/* USER CODE END PD */

/* Private macro -------------------------------------------------------------*/
/* USER CODE BEGIN PM */

/* USER CODE END PM */

/* Private variables ---------------------------------------------------------*/
ADC_HandleTypeDef hadc1;
ADC_HandleTypeDef hadc2;
DMA_HandleTypeDef hdma_adc1;

DAC_HandleTypeDef hdac1;
DMA_HandleTypeDef hdma_dac1_ch1;

TIM_HandleTypeDef htim2;
TIM_HandleTypeDef htim3;

UART_HandleTypeDef huart3;
DMA_HandleTypeDef hdma_usart3_tx;

/* USER CODE BEGIN PV */

/* USER CODE END PV */

/* Private function prototypes -----------------------------------------------*/
void SystemClock_Config(void);
void PeriphCommonClock_Config(void);
static void MX_GPIO_Init(void);
static void MX_DMA_Init(void);
static void MX_ADC1_Init(void);
static void MX_TIM3_Init(void);
static void MX_USART3_UART_Init(void);
static void MX_DAC1_Init(void);
static void MX_TIM2_Init(void);
static void MX_ADC2_Init(void);
/* USER CODE BEGIN PFP */

/* USER CODE END PFP */

/* Private user code ---------------------------------------------------------*/
/* USER CODE BEGIN 0 */
uint32_t adcCombinedBuffer[RAW_DATA_SIZE * 2];
//uint16_t adcBuffer[RAW_DATA_SIZE];
//uint16_t adcBufferRef[RAW_DATA_SIZE];
uint8_t uartTxBuffer[UART_TX_BUF_SIZE];
uint8_t uartTxBufferRef[SAMPLES_PER_SECOND * 3 * 2];
uint8_t uartRxBuffer[UART_RX_BUF_SIZE];

volatile uint16_t uartTxIndex = 0;
volatile uint16_t uartTxIndexRef = 0;
volatile uint8_t uartTxBusy = 0;
volatile uint8_t uartTxRequest = 0;
volatile uint8_t uartRxReceived = 0;

const uint16_t *dac_lut = sine;
uint16_t dac_lut_rx[1000] = { 0 };

//UartPacket uartPacket = { .sync = 0xDEADBEEF, .data = { 0 } };
/* USER CODE END 0 */

/**
 * @brief  The application entry point.
 * @retval int
 */
int main(void) {
	/* USER CODE BEGIN 1 */

	/* USER CODE END 1 */

	/* MCU Configuration--------------------------------------------------------*/

	/* Reset of all peripherals, Initializes the Flash interface and the Systick. */
	HAL_Init();

	/* USER CODE BEGIN Init */

	/* USER CODE END Init */

	/* Configure the system clock */
	SystemClock_Config();

	/* Configure the peripherals common clocks */
	PeriphCommonClock_Config();

	/* USER CODE BEGIN SysInit */

	/* USER CODE END SysInit */

	/* Initialize all configured peripherals */
	MX_GPIO_Init();
	MX_DMA_Init();
	MX_ADC1_Init();
	MX_TIM3_Init();
	MX_USART3_UART_Init();
	MX_DAC1_Init();
	MX_TIM2_Init();
	MX_ADC2_Init();
	/* USER CODE BEGIN 2 */
	HAL_ADCEx_Calibration_Start(&hadc1, ADC_CALIB_OFFSET_LINEARITY, ADC_SINGLE_ENDED);
	HAL_ADCEx_Calibration_Start(&hadc2, ADC_CALIB_OFFSET_LINEARITY, ADC_SINGLE_ENDED);
	HAL_Delay(1000);

	HAL_UART_Receive_IT(&huart3, uartRxBuffer, UART_RX_BUF_SIZE);
	/* USER CODE END 2 */

	/* Infinite loop */
	/* USER CODE BEGIN WHILE */
	volatile uint32_t n_samples = 0;
	volatile uint32_t n_samples_left = 0;
	volatile uint8_t dac_disabled = 0;
	volatile uint8_t adc_single_mode = 0;
	while (1) {
		/* USER CODE END WHILE */

		/* USER CODE BEGIN 3 */
		if (uartTxRequest && !uartTxBusy) {
			uartTxRequest = 0;
			uartTxBusy = 1;
			HAL_UART_Transmit_DMA(&huart3, uartTxBuffer, UART_TX_BUF_SIZE);
//			HAL_UART_Transmit_DMA(&huart3, (uint8_t*) &uartPacket, UART_TX_BUF_SIZE + 4);
//			HAL_GPIO_TogglePin(LD1_GPIO_Port, LD1_Pin);
			n_samples_left -= DATA_SIZE;
			if (n_samples_left == 0) {
				if (!adc_single_mode) {
					HAL_Delay(500);
					HAL_StatusTypeDef err = HAL_UART_Transmit_DMA(&huart3, uartTxBufferRef, n_samples * 2); // n_samples * 2
					if (err) {
						HAL_GPIO_WritePin(LD3_GPIO_Port, LD3_Pin, GPIO_PIN_SET);
					}
				} else {
					adc_single_mode = 0;
				}
				uartTxIndexRef = 0;

				HAL_TIM_Base_Stop(&htim3);
//				HAL_ADC_Stop_DMA(&hadc1);
				HAL_ADCEx_MultiModeStop_DMA(&hadc1);
				HAL_ADC_Stop(&hadc2);

				if (!dac_disabled) {
					HAL_TIM_Base_Stop(&htim2);
					HAL_DAC_Stop_DMA(&hdac1, DAC_CHANNEL_1);
				} else {
					dac_disabled = 0;
				}

//				HAL_Delay(500);
//				uint16_t batch_samples = 1000;
//				uint16_t batch_bytes = batch_samples * 2;
//				uint32_t total_bytes = n_samples * 2;
//				uint32_t bytes_sent = 0;
//				uint32_t timeout_ms = 1000; // 1 sekunda timeoutu na pojedynczą paczkę

//				while (bytes_sent < total_bytes) {
//					// Określamy, ile bajtów wysłać w tej iteracji (pełna paczka lub to, co zostało na końcu)
//					uint16_t bytes_to_send =
//							(total_bytes - bytes_sent > batch_bytes) ? batch_bytes : (total_bytes - bytes_sent);
//
//					// Przesuwamy wskaźnik na odpowiednie miejsce w buforze
//					uint8_t *pData = (uint8_t*) uartTxBufferRef + bytes_sent;
//
//					// Blokujące wysłanie aktualnej paczki
//					HAL_StatusTypeDef err = HAL_UART_Transmit(&huart3, pData, bytes_to_send, timeout_ms);
//
//					if (err != HAL_OK) {
//						HAL_GPIO_WritePin(LD3_GPIO_Port, LD3_Pin, GPIO_PIN_SET);
//						break;
//					}
//
//					bytes_sent += bytes_to_send;
//				}

				HAL_UART_Receive_IT(&huart3, uartRxBuffer, UART_RX_BUF_SIZE);
				HAL_GPIO_WritePin(LD1_GPIO_Port, LD1_Pin, GPIO_PIN_RESET);
			}
		}
		if (uartRxReceived) {
			if (uartRxBuffer[0] == 'S' || uartRxBuffer[0] == 'T' || uartRxBuffer[0] == 'C') {
				n_samples = uartRxBuffer[1] * SAMPLES_PER_SECOND;
				n_samples_left = n_samples;
				uartTxIndexRef = 0;

				if (uartRxBuffer[2] == 0) {
					dac_lut = sine;
				} else if (uartRxBuffer[2] == 1) {
					dac_lut = sine_odd_harmonics;
				} else if (uartRxBuffer[2] == 2) {
					dac_lut = square_wave;
				} else {
					dac_lut = dac_lut_rx;
				}

				switch (uartRxBuffer[3]) {
				case 1:
					__HAL_TIM_SET_AUTORELOAD(&htim2, 1279);
					break; // 50 Hz
				case 2:
					__HAL_TIM_SET_AUTORELOAD(&htim2, 639);
					break; // 100 Hz
				case 4:
					__HAL_TIM_SET_AUTORELOAD(&htim2, 319);
					break; // 200 Hz
				case 5:
					__HAL_TIM_SET_AUTORELOAD(&htim2, 255);
					break; // 250 Hz
				case 8:
					__HAL_TIM_SET_AUTORELOAD(&htim2, 159);
					break; // 400 Hz
				case 10:
					__HAL_TIM_SET_AUTORELOAD(&htim2, 127);
					break; // 500 Hz
				case 16:
					__HAL_TIM_SET_AUTORELOAD(&htim2, 79);
					break; // 800 Hz
				case 20:
					__HAL_TIM_SET_AUTORELOAD(&htim2, 63);
					break; // 1000 Hz
				case 32:
					__HAL_TIM_SET_AUTORELOAD(&htim2, 39);
					break; // 1600 Hz
				case 40:
					__HAL_TIM_SET_AUTORELOAD(&htim2, 31);
					break; // 2000 Hz
				default:
					__HAL_TIM_SET_AUTORELOAD(&htim2, 1279); // Default 50 Hz
					break;
				}
				htim2.Instance->EGR = TIM_EGR_UG;
				__HAL_TIM_CLEAR_FLAG(&htim2, TIM_FLAG_UPDATE);

				if (uartRxBuffer[0] == 'S') {
					HAL_DAC_Start_DMA(&hdac1, DAC_CHANNEL_1, (uint32_t*) dac_lut, 1000, DAC_ALIGN_12B_R);
					HAL_TIM_Base_Start(&htim2);
				} else if (uartRxBuffer[0] == 'C') {
					adc_single_mode = 1;
					dac_disabled = 1;
				} else {
					dac_disabled = 1;
				}

				HAL_Delay(10);

				// HAL_ADC_Start_DMA(&hadc1, (uint32_t*) adcBuffer, RAW_DATA_SIZE);
				HAL_ADC_Start(&hadc2);
				HAL_ADCEx_MultiModeStart_DMA(&hadc1, adcCombinedBuffer, RAW_DATA_SIZE * 2);
				HAL_TIM_Base_Start(&htim3);
				uartRxReceived = 0;

				HAL_GPIO_WritePin(LD1_GPIO_Port, LD1_Pin, GPIO_PIN_SET);
			} else if (uartRxBuffer[0] == 'R') {
				uartRxReceived = 0;
				HAL_StatusTypeDef err = HAL_UART_Receive(&huart3, (uint8_t*) dac_lut_rx, 2000, 1000);
				HAL_UART_Receive_IT(&huart3, uartRxBuffer, UART_RX_BUF_SIZE);
			}
		}
	}
	/* USER CODE END 3 */
}

/**
 * @brief System Clock Configuration
 * @retval None
 */
void SystemClock_Config(void) {
	RCC_OscInitTypeDef RCC_OscInitStruct = { 0 };
	RCC_ClkInitTypeDef RCC_ClkInitStruct = { 0 };

	/** Supply configuration update enable
	 */
	HAL_PWREx_ConfigSupply(PWR_LDO_SUPPLY);

	/** Configure the main internal regulator output voltage
	 */
	__HAL_PWR_VOLTAGESCALING_CONFIG(PWR_REGULATOR_VOLTAGE_SCALE3);

	while (!__HAL_PWR_GET_FLAG(PWR_FLAG_VOSRDY)) {
	}

	/** Macro to configure the PLL clock source
	 */
	__HAL_RCC_PLL_PLLSOURCE_CONFIG(RCC_PLLSOURCE_HSE);

	/** Initializes the RCC Oscillators according to the specified parameters
	 * in the RCC_OscInitTypeDef structure.
	 */
	RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSI | RCC_OSCILLATORTYPE_HSE;
	RCC_OscInitStruct.HSEState = RCC_HSE_BYPASS;
	RCC_OscInitStruct.HSIState = RCC_HSI_DIV1;
	RCC_OscInitStruct.HSICalibrationValue = RCC_HSICALIBRATION_DEFAULT;
	RCC_OscInitStruct.PLL.PLLState = RCC_PLL_NONE;
	if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK) {
		Error_Handler();
	}

	/** Initializes the CPU, AHB and APB buses clocks
	 */
	RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_SYSCLK | RCC_CLOCKTYPE_PCLK1 | RCC_CLOCKTYPE_PCLK2
			| RCC_CLOCKTYPE_D3PCLK1 | RCC_CLOCKTYPE_D1PCLK1;
	RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_HSI;
	RCC_ClkInitStruct.SYSCLKDivider = RCC_SYSCLK_DIV1;
	RCC_ClkInitStruct.AHBCLKDivider = RCC_HCLK_DIV1;
	RCC_ClkInitStruct.APB3CLKDivider = RCC_APB3_DIV1;
	RCC_ClkInitStruct.APB1CLKDivider = RCC_APB1_DIV2;
	RCC_ClkInitStruct.APB2CLKDivider = RCC_APB2_DIV1;
	RCC_ClkInitStruct.APB4CLKDivider = RCC_APB4_DIV1;

	if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_1) != HAL_OK) {
		Error_Handler();
	}
}

/**
 * @brief Peripherals Common Clock Configuration
 * @retval None
 */
void PeriphCommonClock_Config(void) {
	RCC_PeriphCLKInitTypeDef PeriphClkInitStruct = { 0 };

	/** Initializes the peripherals clock
	 */
	PeriphClkInitStruct.PeriphClockSelection = RCC_PERIPHCLK_ADC;
	PeriphClkInitStruct.PLL2.PLL2M = 4;
	PeriphClkInitStruct.PLL2.PLL2N = 128;
	PeriphClkInitStruct.PLL2.PLL2P = 8;
	PeriphClkInitStruct.PLL2.PLL2Q = 2;
	PeriphClkInitStruct.PLL2.PLL2R = 2;
	PeriphClkInitStruct.PLL2.PLL2RGE = RCC_PLL2VCIRANGE_1;
	PeriphClkInitStruct.PLL2.PLL2VCOSEL = RCC_PLL2VCOWIDE;
	PeriphClkInitStruct.PLL2.PLL2FRACN = 0;
	PeriphClkInitStruct.AdcClockSelection = RCC_ADCCLKSOURCE_PLL2;
	if (HAL_RCCEx_PeriphCLKConfig(&PeriphClkInitStruct) != HAL_OK) {
		Error_Handler();
	}
}

/**
 * @brief ADC1 Initialization Function
 * @param None
 * @retval None
 */
static void MX_ADC1_Init(void) {

	/* USER CODE BEGIN ADC1_Init 0 */

	/* USER CODE END ADC1_Init 0 */

	ADC_MultiModeTypeDef multimode = { 0 };
	ADC_ChannelConfTypeDef sConfig = { 0 };

	/* USER CODE BEGIN ADC1_Init 1 */

	/* USER CODE END ADC1_Init 1 */

	/** Common config
	 */
	hadc1.Instance = ADC1;
	hadc1.Init.ClockPrescaler = ADC_CLOCK_ASYNC_DIV1;
	hadc1.Init.Resolution = ADC_RESOLUTION_16B;
	hadc1.Init.ScanConvMode = ADC_SCAN_DISABLE;
	hadc1.Init.EOCSelection = ADC_EOC_SINGLE_CONV;
	hadc1.Init.LowPowerAutoWait = DISABLE;
	hadc1.Init.ContinuousConvMode = DISABLE;
	hadc1.Init.NbrOfConversion = 1;
	hadc1.Init.DiscontinuousConvMode = DISABLE;
	hadc1.Init.ExternalTrigConv = ADC_EXTERNALTRIG_T3_TRGO;
	hadc1.Init.ExternalTrigConvEdge = ADC_EXTERNALTRIGCONVEDGE_RISING;
	hadc1.Init.ConversionDataManagement = ADC_CONVERSIONDATA_DMA_CIRCULAR;
	hadc1.Init.Overrun = ADC_OVR_DATA_OVERWRITTEN;
	hadc1.Init.LeftBitShift = ADC_LEFTBITSHIFT_NONE;
	hadc1.Init.OversamplingMode = DISABLE;
	if (HAL_ADC_Init(&hadc1) != HAL_OK) {
		Error_Handler();
	}

	/** Configure the ADC multi-mode
	 */
	multimode.Mode = ADC_DUALMODE_REGSIMULT;
	multimode.DualModeData = ADC_DUALMODEDATAFORMAT_32_10_BITS;
	multimode.TwoSamplingDelay = ADC_TWOSAMPLINGDELAY_1CYCLE;
	if (HAL_ADCEx_MultiModeConfigChannel(&hadc1, &multimode) != HAL_OK) {
		Error_Handler();
	}

	/** Configure Regular Channel
	 */
	sConfig.Channel = ADC_CHANNEL_2;
	sConfig.Rank = ADC_REGULAR_RANK_1;
	sConfig.SamplingTime = ADC_SAMPLETIME_8CYCLES_5;
	sConfig.SingleDiff = ADC_SINGLE_ENDED;
	sConfig.OffsetNumber = ADC_OFFSET_NONE;
	sConfig.Offset = 0;
	sConfig.OffsetSignedSaturation = DISABLE;
	if (HAL_ADC_ConfigChannel(&hadc1, &sConfig) != HAL_OK) {
		Error_Handler();
	}
	/* USER CODE BEGIN ADC1_Init 2 */

	/* USER CODE END ADC1_Init 2 */

}

/**
 * @brief ADC2 Initialization Function
 * @param None
 * @retval None
 */
static void MX_ADC2_Init(void) {

	/* USER CODE BEGIN ADC2_Init 0 */

	/* USER CODE END ADC2_Init 0 */

	ADC_ChannelConfTypeDef sConfig = { 0 };

	/* USER CODE BEGIN ADC2_Init 1 */

	/* USER CODE END ADC2_Init 1 */

	/** Common config
	 */
	hadc2.Instance = ADC2;
	hadc2.Init.ClockPrescaler = ADC_CLOCK_ASYNC_DIV1;
	hadc2.Init.Resolution = ADC_RESOLUTION_16B;
	hadc2.Init.ScanConvMode = ADC_SCAN_DISABLE;
	hadc2.Init.EOCSelection = ADC_EOC_SINGLE_CONV;
	hadc2.Init.LowPowerAutoWait = DISABLE;
	hadc2.Init.ContinuousConvMode = DISABLE;
	hadc2.Init.NbrOfConversion = 1;
	hadc2.Init.DiscontinuousConvMode = DISABLE;
	hadc2.Init.ConversionDataManagement = ADC_CONVERSIONDATA_DR;
	hadc2.Init.Overrun = ADC_OVR_DATA_OVERWRITTEN;
	hadc2.Init.LeftBitShift = ADC_LEFTBITSHIFT_NONE;
	hadc2.Init.OversamplingMode = DISABLE;
	if (HAL_ADC_Init(&hadc2) != HAL_OK) {
		Error_Handler();
	}

	/** Configure Regular Channel
	 */
	sConfig.Channel = ADC_CHANNEL_2;
	sConfig.Rank = ADC_REGULAR_RANK_1;
	sConfig.SamplingTime = ADC_SAMPLETIME_8CYCLES_5;
	sConfig.SingleDiff = ADC_SINGLE_ENDED;
	sConfig.OffsetNumber = ADC_OFFSET_NONE;
	sConfig.Offset = 0;
	sConfig.OffsetSignedSaturation = DISABLE;
	if (HAL_ADC_ConfigChannel(&hadc2, &sConfig) != HAL_OK) {
		Error_Handler();
	}
	/* USER CODE BEGIN ADC2_Init 2 */

	/* USER CODE END ADC2_Init 2 */

}

/**
 * @brief DAC1 Initialization Function
 * @param None
 * @retval None
 */
static void MX_DAC1_Init(void) {

	/* USER CODE BEGIN DAC1_Init 0 */

	/* USER CODE END DAC1_Init 0 */

	DAC_ChannelConfTypeDef sConfig = { 0 };

	/* USER CODE BEGIN DAC1_Init 1 */

	/* USER CODE END DAC1_Init 1 */

	/** DAC Initialization
	 */
	hdac1.Instance = DAC1;
	if (HAL_DAC_Init(&hdac1) != HAL_OK) {
		Error_Handler();
	}

	/** DAC channel OUT1 config
	 */
	sConfig.DAC_SampleAndHold = DAC_SAMPLEANDHOLD_DISABLE;
	sConfig.DAC_Trigger = DAC_TRIGGER_T2_TRGO;
	sConfig.DAC_OutputBuffer = DAC_OUTPUTBUFFER_ENABLE;
	sConfig.DAC_ConnectOnChipPeripheral = DAC_CHIPCONNECT_DISABLE;
	sConfig.DAC_UserTrimming = DAC_TRIMMING_FACTORY;
	if (HAL_DAC_ConfigChannel(&hdac1, &sConfig, DAC_CHANNEL_1) != HAL_OK) {
		Error_Handler();
	}
	/* USER CODE BEGIN DAC1_Init 2 */

	/* USER CODE END DAC1_Init 2 */

}

/**
 * @brief TIM2 Initialization Function
 * @param None
 * @retval None
 */
static void MX_TIM2_Init(void) {

	/* USER CODE BEGIN TIM2_Init 0 */

	/* USER CODE END TIM2_Init 0 */

	TIM_ClockConfigTypeDef sClockSourceConfig = { 0 };
	TIM_MasterConfigTypeDef sMasterConfig = { 0 };

	/* USER CODE BEGIN TIM2_Init 1 */

	/* USER CODE END TIM2_Init 1 */
	htim2.Instance = TIM2;
	htim2.Init.Prescaler = 0;
	htim2.Init.CounterMode = TIM_COUNTERMODE_UP;
	htim2.Init.Period = 1279;
	htim2.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
	htim2.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_DISABLE;
	if (HAL_TIM_Base_Init(&htim2) != HAL_OK) {
		Error_Handler();
	}
	sClockSourceConfig.ClockSource = TIM_CLOCKSOURCE_INTERNAL;
	if (HAL_TIM_ConfigClockSource(&htim2, &sClockSourceConfig) != HAL_OK) {
		Error_Handler();
	}
	sMasterConfig.MasterOutputTrigger = TIM_TRGO_UPDATE;
	sMasterConfig.MasterSlaveMode = TIM_MASTERSLAVEMODE_DISABLE;
	if (HAL_TIMEx_MasterConfigSynchronization(&htim2, &sMasterConfig) != HAL_OK) {
		Error_Handler();
	}
	/* USER CODE BEGIN TIM2_Init 2 */

	/* USER CODE END TIM2_Init 2 */

}

/**
 * @brief TIM3 Initialization Function
 * @param None
 * @retval None
 */
static void MX_TIM3_Init(void) {

	/* USER CODE BEGIN TIM3_Init 0 */

	/* USER CODE END TIM3_Init 0 */

	TIM_ClockConfigTypeDef sClockSourceConfig = { 0 };
	TIM_MasterConfigTypeDef sMasterConfig = { 0 };

	/* USER CODE BEGIN TIM3_Init 1 */

	/* USER CODE END TIM3_Init 1 */
	htim3.Instance = TIM3;
	htim3.Init.Prescaler = 0;
	htim3.Init.CounterMode = TIM_COUNTERMODE_UP;
	htim3.Init.Period = 199;
	htim3.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
	htim3.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_DISABLE;
	if (HAL_TIM_Base_Init(&htim3) != HAL_OK) {
		Error_Handler();
	}
	sClockSourceConfig.ClockSource = TIM_CLOCKSOURCE_INTERNAL;
	if (HAL_TIM_ConfigClockSource(&htim3, &sClockSourceConfig) != HAL_OK) {
		Error_Handler();
	}
	sMasterConfig.MasterOutputTrigger = TIM_TRGO_UPDATE;
	sMasterConfig.MasterSlaveMode = TIM_MASTERSLAVEMODE_DISABLE;
	if (HAL_TIMEx_MasterConfigSynchronization(&htim3, &sMasterConfig) != HAL_OK) {
		Error_Handler();
	}
	/* USER CODE BEGIN TIM3_Init 2 */

	/* USER CODE END TIM3_Init 2 */

}

/**
 * @brief USART3 Initialization Function
 * @param None
 * @retval None
 */
static void MX_USART3_UART_Init(void) {

	/* USER CODE BEGIN USART3_Init 0 */

	/* USER CODE END USART3_Init 0 */

	/* USER CODE BEGIN USART3_Init 1 */

	/* USER CODE END USART3_Init 1 */
	huart3.Instance = USART3;
	huart3.Init.BaudRate = 460800;
	huart3.Init.WordLength = UART_WORDLENGTH_8B;
	huart3.Init.StopBits = UART_STOPBITS_1;
	huart3.Init.Parity = UART_PARITY_NONE;
	huart3.Init.Mode = UART_MODE_TX_RX;
	huart3.Init.HwFlowCtl = UART_HWCONTROL_NONE;
	huart3.Init.OverSampling = UART_OVERSAMPLING_16;
	huart3.Init.OneBitSampling = UART_ONE_BIT_SAMPLE_DISABLE;
	huart3.Init.ClockPrescaler = UART_PRESCALER_DIV1;
	huart3.AdvancedInit.AdvFeatureInit = UART_ADVFEATURE_NO_INIT;
	if (HAL_UART_Init(&huart3) != HAL_OK) {
		Error_Handler();
	}
	if (HAL_UARTEx_SetTxFifoThreshold(&huart3, UART_TXFIFO_THRESHOLD_1_8) != HAL_OK) {
		Error_Handler();
	}
	if (HAL_UARTEx_SetRxFifoThreshold(&huart3, UART_RXFIFO_THRESHOLD_1_8) != HAL_OK) {
		Error_Handler();
	}
	if (HAL_UARTEx_DisableFifoMode(&huart3) != HAL_OK) {
		Error_Handler();
	}
	/* USER CODE BEGIN USART3_Init 2 */

	/* USER CODE END USART3_Init 2 */

}

/**
 * Enable DMA controller clock
 */
static void MX_DMA_Init(void) {

	/* DMA controller clock enable */
	__HAL_RCC_DMA1_CLK_ENABLE();

	/* DMA interrupt init */
	/* DMA1_Stream0_IRQn interrupt configuration */
	HAL_NVIC_SetPriority(DMA1_Stream0_IRQn, 0, 0);
	HAL_NVIC_EnableIRQ(DMA1_Stream0_IRQn);
	/* DMA1_Stream1_IRQn interrupt configuration */
	HAL_NVIC_SetPriority(DMA1_Stream1_IRQn, 0, 0);
	HAL_NVIC_EnableIRQ(DMA1_Stream1_IRQn);
	/* DMA1_Stream2_IRQn interrupt configuration */
	HAL_NVIC_SetPriority(DMA1_Stream2_IRQn, 0, 0);
	HAL_NVIC_EnableIRQ(DMA1_Stream2_IRQn);

}

/**
 * @brief GPIO Initialization Function
 * @param None
 * @retval None
 */
static void MX_GPIO_Init(void) {
	GPIO_InitTypeDef GPIO_InitStruct = { 0 };
	/* USER CODE BEGIN MX_GPIO_Init_1 */
	/* USER CODE END MX_GPIO_Init_1 */

	/* GPIO Ports Clock Enable */
	__HAL_RCC_GPIOC_CLK_ENABLE();
	__HAL_RCC_GPIOH_CLK_ENABLE();
	__HAL_RCC_GPIOA_CLK_ENABLE();
	__HAL_RCC_GPIOB_CLK_ENABLE();
	__HAL_RCC_GPIOF_CLK_ENABLE();
	__HAL_RCC_GPIOD_CLK_ENABLE();
	__HAL_RCC_GPIOG_CLK_ENABLE();
	__HAL_RCC_GPIOE_CLK_ENABLE();

	/*Configure GPIO pin Output Level */
	HAL_GPIO_WritePin(GPIOB, LD1_Pin | LD3_Pin, GPIO_PIN_RESET);

	/*Configure GPIO pin Output Level */
	HAL_GPIO_WritePin(USB_OTG_FS_PWR_EN_GPIO_Port, USB_OTG_FS_PWR_EN_Pin, GPIO_PIN_RESET);

	/*Configure GPIO pin Output Level */
	HAL_GPIO_WritePin(LD2_GPIO_Port, LD2_Pin, GPIO_PIN_RESET);

	/*Configure GPIO pin : B1_Pin */
	GPIO_InitStruct.Pin = B1_Pin;
	GPIO_InitStruct.Mode = GPIO_MODE_INPUT;
	GPIO_InitStruct.Pull = GPIO_NOPULL;
	HAL_GPIO_Init(B1_GPIO_Port, &GPIO_InitStruct);

	/*Configure GPIO pins : PC1 PC4 PC5 */
	GPIO_InitStruct.Pin = GPIO_PIN_1 | GPIO_PIN_4 | GPIO_PIN_5;
	GPIO_InitStruct.Mode = GPIO_MODE_AF_PP;
	GPIO_InitStruct.Pull = GPIO_NOPULL;
	GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
	GPIO_InitStruct.Alternate = GPIO_AF11_ETH;
	HAL_GPIO_Init(GPIOC, &GPIO_InitStruct);

	/*Configure GPIO pins : PA1 PA2 PA7 */
	GPIO_InitStruct.Pin = GPIO_PIN_1 | GPIO_PIN_2 | GPIO_PIN_7;
	GPIO_InitStruct.Mode = GPIO_MODE_AF_PP;
	GPIO_InitStruct.Pull = GPIO_NOPULL;
	GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
	GPIO_InitStruct.Alternate = GPIO_AF11_ETH;
	HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);

	/*Configure GPIO pins : LD1_Pin LD3_Pin */
	GPIO_InitStruct.Pin = LD1_Pin | LD3_Pin;
	GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
	GPIO_InitStruct.Pull = GPIO_NOPULL;
	GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
	HAL_GPIO_Init(GPIOB, &GPIO_InitStruct);

	/*Configure GPIO pin : PB13 */
	GPIO_InitStruct.Pin = GPIO_PIN_13;
	GPIO_InitStruct.Mode = GPIO_MODE_AF_PP;
	GPIO_InitStruct.Pull = GPIO_NOPULL;
	GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
	GPIO_InitStruct.Alternate = GPIO_AF11_ETH;
	HAL_GPIO_Init(GPIOB, &GPIO_InitStruct);

	/*Configure GPIO pin : USB_OTG_FS_PWR_EN_Pin */
	GPIO_InitStruct.Pin = USB_OTG_FS_PWR_EN_Pin;
	GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
	GPIO_InitStruct.Pull = GPIO_NOPULL;
	GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
	HAL_GPIO_Init(USB_OTG_FS_PWR_EN_GPIO_Port, &GPIO_InitStruct);

	/*Configure GPIO pin : USB_OTG_FS_OVCR_Pin */
	GPIO_InitStruct.Pin = USB_OTG_FS_OVCR_Pin;
	GPIO_InitStruct.Mode = GPIO_MODE_IT_RISING;
	GPIO_InitStruct.Pull = GPIO_NOPULL;
	HAL_GPIO_Init(USB_OTG_FS_OVCR_GPIO_Port, &GPIO_InitStruct);

	/*Configure GPIO pins : PA8 PA11 PA12 */
	GPIO_InitStruct.Pin = GPIO_PIN_8 | GPIO_PIN_11 | GPIO_PIN_12;
	GPIO_InitStruct.Mode = GPIO_MODE_AF_PP;
	GPIO_InitStruct.Pull = GPIO_NOPULL;
	GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
	GPIO_InitStruct.Alternate = GPIO_AF10_OTG1_FS;
	HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);

	/*Configure GPIO pins : PG11 PG13 */
	GPIO_InitStruct.Pin = GPIO_PIN_11 | GPIO_PIN_13;
	GPIO_InitStruct.Mode = GPIO_MODE_AF_PP;
	GPIO_InitStruct.Pull = GPIO_NOPULL;
	GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
	GPIO_InitStruct.Alternate = GPIO_AF11_ETH;
	HAL_GPIO_Init(GPIOG, &GPIO_InitStruct);

	/*Configure GPIO pin : LD2_Pin */
	GPIO_InitStruct.Pin = LD2_Pin;
	GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
	GPIO_InitStruct.Pull = GPIO_NOPULL;
	GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
	HAL_GPIO_Init(LD2_GPIO_Port, &GPIO_InitStruct);

	/* USER CODE BEGIN MX_GPIO_Init_2 */
	/* USER CODE END MX_GPIO_Init_2 */
}

/* USER CODE BEGIN 4 */
int __io_putchar(int ch) {
	HAL_UART_Transmit(&huart3, (uint8_t*) &ch, 1, HAL_MAX_DELAY);
	return ch;
}

//static inline void processAdcBlock(uint16_t *buffer, uint16_t len) {
static inline void processAdcBlock(uint32_t *buffer, uint16_t len) {
	for (uint16_t i = 0; i < len; i += OVR) {
		uint32_t adcResultTemp = 0;
		uint32_t adcResultTemp2 = 0;
		for (uint8_t j = 0; j < OVR; ++j) {
			adcResultTemp += (uint16_t) (buffer[i + j] & 0xFFFF);
			adcResultTemp2 += (uint16_t) ((buffer[i + j] >> 16) & 0xFFFF);
		}
		adcResultTemp >>= P;
		adcResultTemp2 >>= P;
		uartTxBuffer[uartTxIndex++] = adcResultTemp >> 8;
		uartTxBuffer[uartTxIndex++] = adcResultTemp;

		uartTxBufferRef[uartTxIndexRef++] = adcResultTemp2 >> 8;
		uartTxBufferRef[uartTxIndexRef++] = adcResultTemp2;

//		uartPacket.data[uartTxIndex++] = adcResultTemp >> 8;
//		uartPacket.data[uartTxIndex++] = adcResultTemp;
	}
	uartTxIndex = 0;
//	uartTxIndexRef = 0;
	uartTxRequest = 1;
//	if (uartTxIndex >= UART_TX_BUF_SIZE && !uartTxRequest) {
//		uartTxRequest = 1;
//	}
}

void HAL_ADC_ConvHalfCpltCallback(ADC_HandleTypeDef *hadc) {
	if (hadc->Instance == ADC1) {
//		processAdcBlock(&adcBuffer[0], RAW_DATA_SIZE / 2);
		processAdcBlock(&adcCombinedBuffer[0], RAW_DATA_SIZE);
	}
}

void HAL_ADC_ConvCpltCallback(ADC_HandleTypeDef *hadc) {
	if (hadc->Instance == ADC1) {
//		processAdcBlock(&adcBuffer[RAW_DATA_SIZE / 2], RAW_DATA_SIZE / 2);
		processAdcBlock(&adcCombinedBuffer[RAW_DATA_SIZE], RAW_DATA_SIZE);
	}
}

void HAL_UART_TxCpltCallback(UART_HandleTypeDef *huart) {
	if (huart->Instance == USART3) {
		uartTxBusy = 0;
		uartTxIndex = 0;
//		uartTxIndexRef = 0;
	}
}

void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart) {
	if (huart->Instance == USART3) {
		uartRxReceived = 1;
	}
}
/* USER CODE END 4 */

/**
 * @brief  This function is executed in case of error occurrence.
 * @retval None
 */
void Error_Handler(void) {
	/* USER CODE BEGIN Error_Handler_Debug */
	/* User can add his own implementation to report the HAL error return state */
	__disable_irq();
	while (1) {
	}
	/* USER CODE END Error_Handler_Debug */
}

#ifdef  USE_FULL_ASSERT
/**
  * @brief  Reports the name of the source file and the source line number
  *         where the assert_param error has occurred.
  * @param  file: pointer to the source file name
  * @param  line: assert_param error line source number
  * @retval None
  */
void assert_failed(uint8_t *file, uint32_t line)
{
  /* USER CODE BEGIN 6 */
  /* User can add his own implementation to report the file name and line number,
     ex: printf("Wrong parameters value: file %s on line %d\r\n", file, line) */
  /* USER CODE END 6 */
}
#endif /* USE_FULL_ASSERT */
