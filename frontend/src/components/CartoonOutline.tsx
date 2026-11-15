/** Expands the illustration's existing alpha edge; it adds no new spacecraft geometry. */
export function CartoonOutline({ id, radius }: { id: string; radius: number }) {
  return <svg className="cartoon-outline-defs" aria-hidden="true" focusable="false" width="0" height="0">
    <defs><filter id={id} x="-25%" y="-25%" width="150%" height="150%" primitiveUnits="userSpaceOnUse" colorInterpolationFilters="sRGB">
      <feComponentTransfer in="SourceAlpha" result="solid-alpha"><feFuncA type="discrete" tableValues="0 1" /></feComponentTransfer>
      <feMorphology in="solid-alpha" operator="dilate" radius={radius} result="edge" />
      <feFlood floodColor="white" result="white" />
      <feComposite in="white" in2="edge" operator="in" result="outline" />
      <feMerge><feMergeNode in="outline" /><feMergeNode in="SourceGraphic" /></feMerge>
    </filter></defs>
  </svg>;
}
