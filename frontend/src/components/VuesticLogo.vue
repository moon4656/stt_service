<template>
  <svg
    :height="height"
    :width="width"
    viewBox="0 0 430 60"
    xmlns="http://www.w3.org/2000/svg"
    role="img"
    :aria-label="decorative ? undefined : ariaLabel"
    :aria-hidden="decorative ? 'true' : 'false'"
    preserveAspectRatio="xMidYMid meet"
  >
    <!-- 심볼 -->
    <!-- <g transform="translate(0,5)">
      <path
        d="M20 0C8 8 0 22 0 35c0 13 8 27 20 35l10-14c-7-4-12-12-12-21s5-17 12-21L20 0Z"
        :fill="colorsComputed.end"
      />
      <path
        d="M32 0l20 35-20 35-10-14 12-21-12-21L32 0Z"
        :fill="colorsComputed.start"
      />
    </g> -->

    <!-- 워드마크 -->
    <text
      x="80"
      y="42"
      font-size="32"
      font-weight="800"
      font-family="Inter, Pretendard, 'Noto Sans', -apple-system, system-ui, sans-serif"
      :fill="colorsComputed.start"
    >
      HIBIZNET
    </text>
  </svg>
</template>

<script lang="ts" setup>
import { computed } from 'vue'
import { useColors } from 'vuestic-ui'

const { getColor } = useColors()

const props = withDefaults(
  defineProps<{
    height?: number
    width?: number | undefined
    start?: string
    end?: string | undefined
    ariaLabel?: string
    decorative?: boolean
  }>(),
  {
    height: 60,
    width: undefined,
    start: 'primary',
    end: 'info',
    ariaLabel: 'HIBIZNET logo',
    decorative: false,
  },
)

const colorsComputed = computed(() => ({
  start: getColor(props.start),
  end: getColor(props.end || props.start),
}))
</script>
